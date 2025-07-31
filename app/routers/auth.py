from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import logging

from ..auth.oauth_service import OAuthService
from ..models.database import ZidCredential
from ..database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])

class AuthorizeRequest(BaseModel):
    merchant_id: str
    scopes: Optional[list] = None
    redirect_url: Optional[str] = None

class CallbackResponse(BaseModel):
    success: bool
    merchant_id: str
    credential_id: str
    message: str

class TokenStatusResponse(BaseModel):
    merchant_id: str
    is_active: bool
    expires_at: Optional[str] = None
    last_updated: Optional[str] = None

@router.post("/authorize")
async def authorize_merchant(request: AuthorizeRequest):
    """
    Generate OAuth authorization URL for merchant authentication
    
    Args:
        request: Authorization request with merchant_id and optional scopes
        
    Returns:
        Authorization URL for redirect
    """
    try:
        oauth_service = OAuthService()
        auth_url = await oauth_service.generate_authorization_url(
            merchant_id=request.merchant_id,
            scopes=request.scopes
        )
        
        logger.info(f"Generated authorization URL for merchant {request.merchant_id}")
        
        return {
            "authorization_url": auth_url,
            "merchant_id": request.merchant_id,
            "message": "Redirect user to authorization_url to complete OAuth flow"
        }
        
    except Exception as e:
        logger.error(f"Authorization failed for merchant {request.merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")

@router.get("/zid")
async def zid_install_redirect(request: Request):
    """
    Handle Zid app installation redirect (when merchant clicks 'Install on my store')
    
    This is where Zid sends merchants when they click install in the App Store.
    According to Zid's OAuth flow, we immediately redirect to Zid's OAuth authorization.
    The merchant identification happens in the OAuth callback with the authorization code.
    
    Returns:
        Redirect to Zid OAuth authorization
    """
    query_params = dict(request.query_params)
    logger.info(f"Zid install redirect received with params: {query_params}")
    
    try:
        # Generate a unique merchant ID for this installation attempt
        # In a real app, you might extract this from session or other context
        import uuid
        temp_merchant_id = f"install-{uuid.uuid4().hex[:8]}"
        
        oauth_service = OAuthService()
        
        # Generate authorization URL - Zid will identify the merchant during OAuth
        auth_url = await oauth_service.generate_authorization_url(
            merchant_id=temp_merchant_id,
            scopes=["read_orders", "read_products", "read_customers", "webhooks"]
        )
        
        logger.info(f"Redirecting to Zid OAuth authorization for installation {temp_merchant_id}")
        
        # Redirect to Zid's authorization page
        return RedirectResponse(url=auth_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Failed to handle Zid install redirect: {str(e)}")
        raise HTTPException(status_code=500, detail="Installation failed")

@router.get("/zid/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = Query(None, description="Authorization code from Zid"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    error: Optional[str] = Query(None, description="Error from OAuth provider")
):
    """
    Handle OAuth callback from Zid
    
    Args:
        code: Authorization code from Zid
        state: State parameter for verification
        error: Optional error parameter
        
    Returns:
        Callback result with merchant information
    """
    # Log all query parameters for debugging
    query_params = dict(request.query_params)
    logger.info(f"OAuth callback received with params: {query_params}")
    
    # Handle OAuth errors
    if error:
        logger.error(f"OAuth callback received error: {error}")
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    # Handle missing required parameters
    if not code or not state:
        logger.warning(f"OAuth callback missing required parameters. Code: {bool(code)}, State: {bool(state)}")
        return {
            "error": "Missing required OAuth parameters",
            "message": "This endpoint expects 'code' and 'state' parameters from Zid OAuth flow",
            "received_params": query_params,
            "instructions": "Please initiate OAuth flow by calling POST /auth/authorize first"
        }
    
    try:
        oauth_service = OAuthService()
        
        # Get client information for audit logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Handle the callback
        result = await oauth_service.handle_callback(
            code=code,
            state=state,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        logger.info(f"OAuth callback completed for merchant {result['merchant_id']}")
        
        return CallbackResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth callback processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@router.get("/status/{merchant_id}")
async def get_auth_status(
    merchant_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get authentication status for a merchant
    
    Args:
        merchant_id: Merchant identifier
        
    Returns:
        Authentication status information
    """
    try:
        stmt = select(ZidCredential).where(
            ZidCredential.merchant_id == merchant_id,
            ZidCredential.is_active == True
        )
        result = await db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if not credential:
            return TokenStatusResponse(
                merchant_id=merchant_id,
                is_active=False
            )
        
        return TokenStatusResponse(
            merchant_id=merchant_id,
            is_active=True,
            expires_at=credential.expires_at.isoformat() if credential.expires_at else None,
            last_updated=credential.updated_at.isoformat() if credential.updated_at else None
        )
        
    except Exception as e:
        logger.error(f"Failed to get auth status for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve authentication status")

@router.post("/refresh/{merchant_id}")
async def refresh_merchant_tokens(
    merchant_id: str,
    request: Request
):
    """
    Refresh expired tokens for a merchant
    
    Args:
        merchant_id: Merchant identifier
        
    Returns:
        Token refresh confirmation
    """
    try:
        oauth_service = OAuthService()
        
        # Get client information for audit logging
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        result = await oauth_service.refresh_tokens(
            merchant_id=merchant_id,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        logger.info(f"Tokens refreshed for merchant {merchant_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to refresh tokens for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Token refresh failed")

@router.post("/revoke/{merchant_id}")
async def revoke_merchant_auth(
    merchant_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Revoke authentication for a merchant
    
    Args:
        merchant_id: Merchant identifier
        
    Returns:
        Revocation confirmation
    """
    try:
        stmt = select(ZidCredential).where(ZidCredential.merchant_id == merchant_id)
        result = await db.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if not credential:
            raise HTTPException(status_code=404, detail="Merchant authentication not found")
        
        # Deactivate the credential
        credential.is_active = False
        await db.commit()
        
        logger.info(f"Revoked authentication for merchant {merchant_id}")
        
        return {
            "success": True,
            "merchant_id": merchant_id,
            "message": "Authentication revoked successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke auth for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to revoke authentication")

@router.get("/test-authorize/{merchant_id}")
async def test_authorization_flow(merchant_id: str):
    """
    Test endpoint to generate OAuth authorization URL for a merchant
    
    Args:
        merchant_id: Test merchant identifier
        
    Returns:
        Authorization URL for testing
    """
    try:
        oauth_service = OAuthService()
        auth_url = await oauth_service.generate_authorization_url(
            merchant_id=merchant_id,
            scopes=["read_orders", "read_products", "read_customers", "webhooks"]
        )
        
        return {
            "merchant_id": merchant_id,
            "authorization_url": auth_url,
            "instructions": "Visit the authorization_url in your browser to complete OAuth flow"
        }
        
    except Exception as e:
        logger.error(f"Test authorization failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate test authorization URL")

@router.get("/health")
async def auth_health_check():
    """Health check endpoint for authentication service"""
    try:
        oauth_service = OAuthService()
        return {
            "status": "healthy",
            "service": "authentication",
            "oauth_configured": bool(oauth_service.client_id and oauth_service.client_secret),
            "zid_install_url": "https://zid-s7xi6.ondigitalocean.app/auth/zid",
            "zid_callback_url": "https://zid-s7xi6.ondigitalocean.app/auth/zid/callback",
            "endpoints": {
                "zid_install": "/auth/zid",
                "zid_callback": "/auth/zid/callback",
                "authorize": "/auth/authorize",
                "callback": "/auth/callback", 
                "test": "/auth/test-authorize/{merchant_id}",
                "status": "/auth/status/{merchant_id}",
                "refresh": "/auth/refresh/{merchant_id}",
                "revoke": "/auth/revoke/{merchant_id}"
            }
        }
    except Exception as e:
        logger.error(f"Auth health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable")