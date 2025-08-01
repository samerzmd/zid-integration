import asyncio
import httpx
import logging
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.database import ZidCredential
from ..database import get_db
from ..auth.token_manager import TokenManager
from ..auth.oauth_service import OAuthService
from ..config import settings

logger = logging.getLogger(__name__)

class ZidAPIClient:
    """
    Authenticated API client for Zid e-commerce platform
    
    Implements Zid's dual-header authentication pattern:
    - X-Manager-Token: Uses access_token from OAuth
    - Authorization: Bearer uses authorization token from OAuth
    
    Features:
    - Automatic token refresh on expiry
    - Rate limiting and retry logic
    - Comprehensive error handling
    - Token validation and health checks
    """
    
    def __init__(self, merchant_id: str):
        self.merchant_id = merchant_id
        self.base_url = "https://api.zid.sa"
        self.token_manager = TokenManager()
        self.oauth_service = OAuthService()
        
        # API client configuration
        self.timeout = httpx.Timeout(30.0)
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        
        # Rate limiting (Zid's limits)
        self.rate_limit_per_minute = 120
        self.rate_limit_window = 60  # seconds
        
        # Token expiry buffer
        self.token_refresh_buffer = timedelta(minutes=30)
    
    async def _get_credentials(self) -> Optional[ZidCredential]:
        """Retrieve active credentials for the merchant"""
        try:
            async with get_db() as db:
                stmt = select(ZidCredential).where(
                    ZidCredential.merchant_id == self.merchant_id,
                    ZidCredential.is_active == True
                )
                result = await db.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to retrieve credentials for merchant {self.merchant_id}: {str(e)}")
            return None
    
    async def _decrypt_tokens(self, credential: ZidCredential) -> Optional[Dict[str, str]]:
        """Decrypt stored tokens"""
        try:
            access_token = await self.token_manager.decrypt_token(credential.access_token)
            authorization_token = await self.token_manager.decrypt_token(credential.authorization_token)
            refresh_token = await self.token_manager.decrypt_token(credential.refresh_token)
            
            if not all([access_token, authorization_token, refresh_token]):
                logger.error(f"Failed to decrypt tokens for merchant {self.merchant_id}")
                return None
            
            return {
                "access_token": access_token,
                "authorization_token": authorization_token,
                "refresh_token": refresh_token
            }
        except Exception as e:
            logger.error(f"Token decryption failed for merchant {self.merchant_id}: {str(e)}")
            return None
    
    async def _should_refresh_token(self, credential: ZidCredential) -> bool:
        """Check if tokens should be refreshed based on expiry"""
        if not credential.expires_at:
            return False
        
        # Refresh if token expires within the buffer window
        refresh_threshold = datetime.utcnow() + self.token_refresh_buffer
        return credential.expires_at <= refresh_threshold
    
    async def _refresh_tokens_if_needed(self, credential: ZidCredential) -> bool:
        """Refresh tokens if they're close to expiry"""
        if not await self._should_refresh_token(credential):
            return True
        
        try:
            logger.info(f"Refreshing tokens for merchant {self.merchant_id}")
            await self.oauth_service.refresh_tokens(
                merchant_id=self.merchant_id
            )
            return True
        except Exception as e:
            logger.error(f"Token refresh failed for merchant {self.merchant_id}: {str(e)}")
            return False
    
    async def _get_headers(self) -> Optional[Dict[str, str]]:
        """Get authenticated headers for API requests"""
        credential = await self._get_credentials()
        if not credential:
            logger.error(f"No active credentials found for merchant {self.merchant_id}")
            return None
        
        # Refresh tokens if needed
        if not await self._refresh_tokens_if_needed(credential):
            return None
        
        # Get fresh credential after potential refresh
        credential = await self._get_credentials()
        if not credential:
            return None
        
        # Decrypt tokens
        tokens = await self._decrypt_tokens(credential)
        if not tokens:
            return None
        
        # Build Zid's required headers according to API documentation
        headers = {
            # Authentication headers
            "Access-Token": tokens["access_token"],  # Required by Zid API
            "Authorization": f"Bearer {tokens['authorization_token']}",  # Required by Zid API
            
            # Required Zid API headers
            "Store-Id": self.merchant_id,  # Use merchant_id as Store-Id
            "Role": "Manager",  # Required role for API access
            "Accept-Language": "all-languages",  # Get both Arabic and English content
            
            # Standard headers
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"ZidIntegration/1.0.0 (Merchant: {self.merchant_id})"
        }
        
        return headers
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make authenticated API request with retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/products')
            data: Request body data
            params: Query parameters
            headers: Additional headers
            
        Returns:
            API response data or None if failed
        """
        # Get authenticated headers
        auth_headers = await self._get_headers()
        if not auth_headers:
            logger.error(f"Failed to get authentication headers for merchant {self.merchant_id}")
            return None
        
        # Merge with additional headers
        if headers:
            auth_headers.update(headers)
        
        url = f"{self.base_url}{endpoint}"
        
        # Retry logic
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        json=data if method in ["POST", "PUT", "PATCH"] else None,
                        params=params,
                        headers=auth_headers
                    )
                    
                    # Log request details
                    logger.info(f"Zid API {method} {endpoint} -> {response.status_code}")
                    
                    # Handle response
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 401:
                        logger.warning(f"Authentication failed for merchant {self.merchant_id}")
                        # Try to refresh tokens and retry once
                        if attempt == 0:
                            await self.oauth_service.refresh_tokens(self.merchant_id)
                            continue
                        return None
                    elif response.status_code in [429, 502, 503, 504]:
                        # Rate limiting or server errors - retry with backoff
                        if attempt < self.max_retries - 1:
                            wait_time = self.retry_delay * (2 ** attempt)
                            logger.warning(f"API request failed ({response.status_code}), retrying in {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                    else:
                        logger.error(f"API request failed: {response.status_code} - {response.text}")
                        return None
                        
            except httpx.RequestError as e:
                logger.error(f"HTTP request failed (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(wait_time)
                    continue
                return None
        
        logger.error(f"API request failed after {self.max_retries} attempts")
        return None
    
    # Convenience methods for different HTTP verbs
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make GET request to Zid API"""
        return await self._make_request("GET", endpoint, params=params)
    
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make POST request to Zid API"""
        return await self._make_request("POST", endpoint, data=data)
    
    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make PUT request to Zid API"""
        return await self._make_request("PUT", endpoint, data=data)
    
    async def delete(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make DELETE request to Zid API"""
        return await self._make_request("DELETE", endpoint)
    
    async def validate_tokens(self) -> Dict[str, Any]:
        """
        Validate stored tokens and return status
        
        Returns:
            Dictionary with validation results
        """
        try:
            credential = await self._get_credentials()
            if not credential:
                return {
                    "valid": False,
                    "error": "No credentials found",
                    "merchant_id": self.merchant_id
                }
            
            # Check if tokens can be decrypted
            tokens = await self._decrypt_tokens(credential)
            if not tokens:
                return {
                    "valid": False,
                    "error": "Token decryption failed",
                    "merchant_id": self.merchant_id,
                    "expires_at": credential.expires_at.isoformat() if credential.expires_at else None
                }
            
            # Check expiry
            is_expired = credential.expires_at and credential.expires_at <= datetime.utcnow()
            needs_refresh = await self._should_refresh_token(credential)
            
            return {
                "valid": True,
                "merchant_id": self.merchant_id,
                "is_active": credential.is_active,
                "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
                "is_expired": is_expired,
                "needs_refresh": needs_refresh,
                "last_updated": credential.updated_at.isoformat() if credential.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"Token validation failed for merchant {self.merchant_id}: {str(e)}")
            return {
                "valid": False,
                "error": str(e),
                "merchant_id": self.merchant_id
            }