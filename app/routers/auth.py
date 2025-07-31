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
        
        # Get merchant information using the access token
        authenticated_client = ZidAPIClient(access_token=token_response.access_token)
        try:
            logger.info(f"Attempting to fetch merchant info with token: {token_response.access_token[:50]}...")
            headers = authenticated_client._get_manager_headers()
            logger.info(f"Using headers: Authorization={headers.get('Authorization', 'None')[:50]}..., X-MANAGER-TOKEN={headers.get('X-MANAGER-TOKEN', 'None')[:50]}...")
            merchant_info = await authenticated_client.get_merchant_info()
            # Extract manager ID from the profile response
            merchant_id = str(merchant_info.get("id", "unknown"))
            logger.info(f"Successfully retrieved merchant ID: {merchant_id}")
        except Exception as e:
            logger.warning(f"Could not fetch merchant info: {str(e)}, using fallback")
            # Fallback: extract from token or use a default
            merchant_id = "default_merchant"
        finally:
            await authenticated_client.close()
        
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