from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from ..auth import AuthService, get_authorization_url
from ..zid_client import ZidAPIClient
from ..schemas import MerchantTokenCreate, MerchantTokenResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/authorize")
async def initiate_oauth():
    """Redirect to Zid OAuth2 authorization page"""
    auth_url = get_authorization_url()
    return {"authorization_url": auth_url}


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle OAuth callback and exchange code for token"""
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    client = ZidAPIClient()
    auth_service = AuthService(db)
    
    try:
        # Exchange code for token
        token_response = await client.exchange_code_for_token(code, state)
        
        # Extract merchant_id from token or make API call to get it
        # For now, we'll use a placeholder - in real implementation, 
        # you'd get this from the token payload or a separate API call
        merchant_id = "merchant_placeholder"  # TODO: Get actual merchant ID
        
        # Save token to database
        token_create = MerchantTokenCreate(
            merchant_id=merchant_id,
            access_token=token_response.access_token,
            refresh_token=token_response.refresh_token,
            expires_in=token_response.expires_in
        )
        
        saved_token = await auth_service.save_merchant_token(token_create)
        
        return {
            "message": "Authentication successful",
            "merchant_id": saved_token.merchant_id
        }
    
    except Exception as e:
        logger.error(f"OAuth callback error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")
    
    finally:
        await client.close()