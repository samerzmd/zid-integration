from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from .models import MerchantToken
from .zid_client import ZidAPIClient
from .schemas import MerchantTokenCreate, TokenResponse
from .config import settings
import logging

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def save_merchant_token(self, token_data: MerchantTokenCreate) -> MerchantToken:
        """Save or update merchant token in database"""
        # Check if token already exists
        stmt = select(MerchantToken).where(MerchantToken.merchant_id == token_data.merchant_id)
        result = await self.db.execute(stmt)
        existing_token = result.scalar_one_or_none()
        
        if existing_token:
            # Update existing token
            existing_token.access_token = token_data.access_token
            existing_token.authorization_token = token_data.authorization_token
            existing_token.refresh_token = token_data.refresh_token
            existing_token.expires_in = token_data.expires_in
            existing_token.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing_token)
            return existing_token
        else:
            # Create new token
            db_token = MerchantToken(**token_data.dict())
            self.db.add(db_token)
            await self.db.commit()
            await self.db.refresh(db_token)
            return db_token
    
    async def get_merchant_token(self, merchant_id: str) -> MerchantToken:
        """Get merchant token from database"""
        stmt = select(MerchantToken).where(MerchantToken.merchant_id == merchant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def is_token_expired(self, token: MerchantToken) -> bool:
        """Check if token is expired"""
        if not token.created_at or not token.expires_in:
            return True
        
        expiry_time = token.created_at + timedelta(seconds=token.expires_in)
        return datetime.utcnow() >= expiry_time
    
    async def refresh_token_if_needed(self, merchant_id: str) -> MerchantToken:
        """Refresh token if it's expired"""
        token = await self.get_merchant_token(merchant_id)
        if not token:
            raise ValueError(f"No token found for merchant {merchant_id}")
        
        if await self.is_token_expired(token):
            logger.info(f"Token expired for merchant {merchant_id}, refreshing...")
            
            client = ZidAPIClient()
            try:
                new_token_response = await client.refresh_access_token(token.refresh_token)
                
                # Update token in database
                token_create = MerchantTokenCreate(
                    merchant_id=merchant_id,
                    access_token=new_token_response.access_token,
                    authorization_token=new_token_response.Authorization,
                    refresh_token=new_token_response.refresh_token,
                    expires_in=new_token_response.expires_in
                )
                
                updated_token = await self.save_merchant_token(token_create)
                logger.info(f"Token refreshed successfully for merchant {merchant_id}")
                return updated_token
                
            finally:
                await client.close()
        
        return token
    
    async def get_valid_token(self, merchant_id: str) -> tuple[str, str]:
        """Get valid tokens (access_token, authorization_token), refreshing if necessary"""
        token = await self.refresh_token_if_needed(merchant_id)
        return token.access_token, token.authorization_token


def get_authorization_url() -> str:
    """Generate Zid OAuth2 authorization URL"""
    oauth_base_url = "https://oauth.zid.sa"
    params = {
        "response_type": "code",
        "client_id": settings.zid_client_id,
        "redirect_uri": settings.zid_redirect_uri,
        "scope": "read write"  # Adjust scopes as needed
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{oauth_base_url}/oauth/authorize?{query_string}"