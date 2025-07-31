import os
import secrets
import hashlib
from urllib.parse import urlencode
from typing import Optional, Dict, Any, Tuple
import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
import logging

from ..models.database import ZidCredential, OAuthState, TokenAuditLog
from ..database import get_db
from .token_manager import TokenManager
from ..config import settings

logger = logging.getLogger(__name__)

class OAuthService:
    """Zid OAuth 2.0 service with triple token system support"""
    
    def __init__(self):
        self.client_id = settings.zid_client_id
        self.client_secret = settings.zid_client_secret
        self.redirect_uri = settings.zid_redirect_uri
        self.oauth_base_url = "https://oauth.zid.sa"
        self.token_manager = TokenManager()
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            raise ValueError("Missing required OAuth environment variables")
    
    async def generate_authorization_url(self, merchant_id: str, scopes: Optional[list] = None) -> str:
        """
        Generate OAuth authorization URL with secure state parameter
        
        Args:
            merchant_id: Unique merchant identifier
            scopes: List of OAuth scopes to request
            
        Returns:
            Authorization URL for redirect
        """
        if scopes is None:
            scopes = ["read_orders", "read_products", "read_customers", "webhooks"]
        
        try:
            # Generate secure state parameter
            state = secrets.token_urlsafe(32)
            state_hash = hashlib.sha256(state.encode()).hexdigest()
            
            # Store state in database for verification
            async with get_db() as db:
                oauth_state = OAuthState(
                    state_hash=state_hash,
                    merchant_id=merchant_id,
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(minutes=settings.oauth_state_expiry_minutes)
                )
                db.add(oauth_state)
                await db.commit()
            
            # Build authorization URL
            params = {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": " ".join(scopes),
                "state": state
            }
            
            auth_url = f"{self.oauth_base_url}/oauth/authorize?{urlencode(params)}"
            
            # Log authorization initiation
            await self._log_token_action(
                merchant_id=merchant_id,
                action="oauth_initiated",
                success=True,
                ip_address=None,
                user_agent=None
            )
            
            logger.info(f"Generated OAuth URL for merchant {merchant_id}")
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate OAuth URL for merchant {merchant_id}: {str(e)}")
            await self._log_token_action(
                merchant_id=merchant_id,
                action="oauth_initiated",
                success=False,
                error_message=str(e)
            )
            raise HTTPException(status_code=500, detail="Failed to generate authorization URL")
    
    async def handle_callback(self, code: str, state: str, 
                            ip_address: Optional[str] = None, 
                            user_agent: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle OAuth callback with comprehensive error handling
        
        Args:
            code: Authorization code from Zid
            state: State parameter for CSRF protection
            ip_address: Client IP address for audit logging
            user_agent: Client user agent for audit logging
            
        Returns:
            Dictionary with callback result and merchant information
        """
        merchant_id = None
        try:
            # Verify and get merchant_id from state
            merchant_id = await self._verify_state(state)
            
            # Exchange authorization code for tokens
            token_response = await self._exchange_code_for_tokens(code)
            
            # Store tokens securely with encryption
            credential_id = await self._store_tokens(merchant_id, token_response)
            
            # Clean up used state
            await self._cleanup_state(state)
            
            # Log successful authentication
            await self._log_token_action(
                merchant_id=merchant_id,
                action="tokens_created",
                success=True,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"OAuth callback completed successfully for merchant {merchant_id}")
            
            return {
                "success": True,
                "merchant_id": merchant_id,
                "credential_id": credential_id,
                "message": "Authentication successful"
            }
            
        except HTTPException:
            if merchant_id:
                await self._log_token_action(
                    merchant_id=merchant_id,
                    action="tokens_created",
                    success=False,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            raise
        except Exception as e:
            logger.error(f"OAuth callback error: {str(e)}")
            if merchant_id:
                await self._log_token_action(
                    merchant_id=merchant_id,
                    action="tokens_created",
                    success=False,
                    error_message=str(e),
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            raise HTTPException(status_code=500, detail="Authentication failed")
    
    async def _verify_state(self, state: str) -> str:
        """Verify OAuth state parameter and return merchant_id"""
        state_hash = hashlib.sha256(state.encode()).hexdigest()
        
        async with get_db() as db:
            stmt = select(OAuthState).where(
                OAuthState.state_hash == state_hash,
                OAuthState.expires_at > datetime.utcnow(),
                OAuthState.used == False
            )
            result = await db.execute(stmt)
            oauth_state = result.scalar_one_or_none()
            
            if not oauth_state:
                logger.warning(f"Invalid or expired state parameter: {state_hash[:8]}...")
                raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
            
            # Mark state as used
            oauth_state.used = True
            await db.commit()
            
            return oauth_state.merchant_id
    
    async def _exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for Zid triple token system"""
        token_url = f"{self.oauth_base_url}/oauth/token"
        
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(token_url, data=data, headers=headers)
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Token exchange failed: {response.status_code} - {error_detail}")
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Token exchange failed: {error_detail}"
                    )
                
                token_data = response.json()
                
                # Validate Zid's triple token response
                required_fields = ["access_token", "Authorization", "refresh_token"]
                missing_fields = [field for field in required_fields if field not in token_data]
                
                if missing_fields:
                    logger.error(f"Missing token fields: {missing_fields}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Incomplete token response: missing {missing_fields}"
                    )
                
                logger.info("Token exchange completed successfully")
                return token_data
                
        except httpx.RequestError as e:
            logger.error(f"HTTP request failed during token exchange: {str(e)}")
            raise HTTPException(status_code=503, detail="OAuth service unavailable")
    
    async def _store_tokens(self, merchant_id: str, token_response: Dict[str, Any]) -> str:
        """Store Zid triple tokens securely with encryption"""
        async with get_db() as db:
            # Check if credential already exists
            stmt = select(ZidCredential).where(ZidCredential.merchant_id == merchant_id)
            result = await db.execute(stmt)
            existing_credential = result.scalar_one_or_none()
            
            # Calculate token expiration (Zid tokens expire in 1 year)
            expires_at = datetime.utcnow() + timedelta(seconds=token_response.get("expires_in", 31536000))
            
            # Encrypt all three tokens
            encrypted_access_token = await self.token_manager.encrypt_token(
                token_response["access_token"]
            )
            encrypted_authorization_token = await self.token_manager.encrypt_token(
                token_response["Authorization"]
            )
            encrypted_refresh_token = await self.token_manager.encrypt_token(
                token_response["refresh_token"]
            )
            
            if existing_credential:
                # Update existing credential
                existing_credential.access_token = encrypted_access_token
                existing_credential.authorization_token = encrypted_authorization_token
                existing_credential.refresh_token = encrypted_refresh_token
                existing_credential.expires_at = expires_at
                existing_credential.updated_at = datetime.utcnow()
                existing_credential.is_active = True
                
                credential_id = existing_credential.id
                logger.info(f"Updated existing credentials for merchant {merchant_id}")
                
            else:
                # Create new credential
                credential = ZidCredential(
                    merchant_id=merchant_id,
                    access_token=encrypted_access_token,
                    authorization_token=encrypted_authorization_token,
                    refresh_token=encrypted_refresh_token,
                    expires_at=expires_at,
                    is_active=True
                )
                
                db.add(credential)
                await db.flush()
                credential_id = credential.id
                logger.info(f"Created new credentials for merchant {merchant_id}")
            
            await db.commit()
            return credential_id
    
    async def _cleanup_state(self, state: str):
        """Clean up used OAuth state"""
        state_hash = hashlib.sha256(state.encode()).hexdigest()
        
        async with get_db() as db:
            stmt = update(OAuthState).where(
                OAuthState.state_hash == state_hash
            ).values(used=True)
            await db.execute(stmt)
            await db.commit()
    
    async def refresh_tokens(self, merchant_id: str,
                           ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None) -> Dict[str, Any]:
        """
        Refresh expired tokens for a merchant
        
        Args:
            merchant_id: Merchant identifier
            ip_address: Client IP for audit logging
            user_agent: Client user agent for audit logging
            
        Returns:
            Dictionary with refresh result
        """
        try:
            async with get_db() as db:
                # Get existing credential
                stmt = select(ZidCredential).where(ZidCredential.merchant_id == merchant_id)
                result = await db.execute(stmt)
                credential = result.scalar_one_or_none()
                
                if not credential:
                    raise HTTPException(status_code=404, detail="Merchant authentication not found")
                
                # Decrypt refresh token
                refresh_token = await self.token_manager.decrypt_token(credential.refresh_token)
                if not refresh_token:
                    logger.error(f"Failed to decrypt refresh token for merchant {merchant_id}")
                    raise HTTPException(status_code=400, detail="Invalid refresh token")
                
                # Exchange refresh token for new tokens
                new_tokens = await self._exchange_refresh_token(refresh_token)
                
                # Update stored tokens
                await self._update_tokens(credential, new_tokens)
                
                # Log successful refresh
                await self._log_token_action(
                    merchant_id=merchant_id,
                    action="tokens_refreshed",
                    success=True,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                logger.info(f"Tokens refreshed successfully for merchant {merchant_id}")
                
                return {
                    "success": True,
                    "merchant_id": merchant_id,
                    "message": "Tokens refreshed successfully"
                }
                
        except HTTPException:
            await self._log_token_action(
                merchant_id=merchant_id,
                action="tokens_refreshed",
                success=False,
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise
        except Exception as e:
            logger.error(f"Token refresh failed for merchant {merchant_id}: {str(e)}")
            await self._log_token_action(
                merchant_id=merchant_id,
                action="tokens_refreshed",
                success=False,
                error_message=str(e),
                ip_address=ip_address,
                user_agent=user_agent
            )
            raise HTTPException(status_code=500, detail="Token refresh failed")
    
    async def _exchange_refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Exchange refresh token for new access tokens"""
        token_url = f"{self.oauth_base_url}/oauth/token"
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(token_url, data=data, headers=headers)
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Token refresh failed: {response.status_code} - {error_detail}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Token refresh failed: {error_detail}"
                    )
                
                token_data = response.json()
                
                # Validate response has required tokens
                required_fields = ["access_token", "Authorization"]
                missing_fields = [field for field in required_fields if field not in token_data]
                
                if missing_fields:
                    logger.error(f"Missing token fields in refresh response: {missing_fields}")
                    raise HTTPException(
                        status_code=400,
                        detail=f"Incomplete refresh response: missing {missing_fields}"
                    )
                
                logger.info("Token refresh exchange completed successfully")
                return token_data
                
        except httpx.RequestError as e:
            logger.error(f"HTTP request failed during token refresh: {str(e)}")
            raise HTTPException(status_code=503, detail="OAuth service unavailable")
    
    async def _update_tokens(self, credential: ZidCredential, token_response: Dict[str, Any]):
        """Update existing credential with new tokens"""
        # Calculate new expiration
        expires_at = datetime.utcnow() + timedelta(seconds=token_response.get("expires_in", 31536000))
        
        # Encrypt new tokens
        encrypted_access_token = await self.token_manager.encrypt_token(
            token_response["access_token"]
        )
        encrypted_authorization_token = await self.token_manager.encrypt_token(
            token_response["Authorization"]
        )
        
        # Update refresh token if provided (some OAuth providers issue new refresh tokens)
        if "refresh_token" in token_response:
            encrypted_refresh_token = await self.token_manager.encrypt_token(
                token_response["refresh_token"]
            )
            credential.refresh_token = encrypted_refresh_token
        
        # Update tokens
        credential.access_token = encrypted_access_token
        credential.authorization_token = encrypted_authorization_token
        credential.expires_at = expires_at
        credential.updated_at = datetime.utcnow()
        credential.is_active = True
        
        # Commit changes through the existing session
        async with get_db() as db:
            await db.merge(credential)
            await db.commit()
    
    async def _log_token_action(self, merchant_id: str, action: str, success: bool,
                               ip_address: Optional[str] = None, 
                               user_agent: Optional[str] = None,
                               error_message: Optional[str] = None):
        """Log token-related actions for audit trail"""
        try:
            async with get_db() as db:
                audit_log = TokenAuditLog(
                    merchant_id=merchant_id,
                    action=action,
                    success=success,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    error_message=error_message
                )
                db.add(audit_log)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to log token action: {str(e)}")
            # Don't raise here - audit logging shouldn't break the flow