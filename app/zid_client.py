import httpx
from typing import Optional, Dict, Any, List
from .config import settings
from .schemas import TokenResponse


class ZidAPIClient:
    def __init__(self, access_token: Optional[str] = None):
        self.base_url = settings.zid_api_base_url
        self.access_token = access_token
        self.client = httpx.AsyncClient()
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    async def exchange_code_for_token(self, code: str, state: Optional[str] = None) -> TokenResponse:
        """Exchange authorization code for access token"""
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.zid_client_id,
            "client_secret": settings.zid_client_secret,
            "code": code,
            "redirect_uri": settings.zid_redirect_uri
        }
        
        response = await self.client.post(
            f"{self.base_url}/oauth/token",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return TokenResponse(**response.json())
    
    async def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token"""
        data = {
            "grant_type": "refresh_token",
            "client_id": settings.zid_client_id,
            "client_secret": settings.zid_client_secret,
            "refresh_token": refresh_token
        }
        
        response = await self.client.post(
            f"{self.base_url}/oauth/token",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return TokenResponse(**response.json())
    
    async def get_products(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get list of products"""
        params = {
            "page": page,
            "page_size": page_size
        }
        
        response = await self.client.get(
            f"{self.base_url}/v1/managers/products",
            params=params,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_product_stock(self, product_id: int) -> Dict[str, Any]:
        """Get product stock information"""
        response = await self.client.get(
            f"{self.base_url}/v1/managers/products/{product_id}/stocks",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def get_orders(self, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Get list of orders"""
        params = {
            "page": page,
            "page_size": page_size
        }
        
        response = await self.client.get(
            f"{self.base_url}/v1/managers/orders",
            params=params,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def update_product_price(self, product_id: int, price: float) -> Dict[str, Any]:
        """Update product price"""
        data = {
            "price": price
        }
        
        response = await self.client.patch(
            f"{self.base_url}/v1/managers/products/{product_id}",
            json=data,
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()