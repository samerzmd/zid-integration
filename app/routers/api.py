from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging

from ..api.zid_client import ZidAPIClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["zid-api"])

class APITestResponse(BaseModel):
    success: bool
    merchant_id: str
    endpoint: str
    data: Optional[dict] = None
    error: Optional[str] = None

class TokenValidationResponse(BaseModel):
    valid: bool
    merchant_id: str
    is_active: Optional[bool] = None
    expires_at: Optional[str] = None
    is_expired: Optional[bool] = None
    needs_refresh: Optional[bool] = None
    last_updated: Optional[str] = None
    error: Optional[str] = None

@router.get("/test/{merchant_id}")
async def test_api_client(
    merchant_id: str,
    endpoint: str = Query(default="/store", description="Zid API endpoint to test")
):
    """
    Test the Zid API client with a merchant's stored tokens
    
    Args:
        merchant_id: Merchant identifier
        endpoint: Zid API endpoint to test (default: /store)
        
    Returns:
        API test results
    """
    try:
        client = ZidAPIClient(merchant_id)
        
        # Make API request
        data = await client.get(endpoint)
        
        if data is not None:
            logger.info(f"API test successful for merchant {merchant_id} on {endpoint}")
            return APITestResponse(
                success=True,
                merchant_id=merchant_id,
                endpoint=endpoint,
                data=data
            )
        else:
            logger.warning(f"API test failed for merchant {merchant_id} on {endpoint}")
            return APITestResponse(
                success=False,
                merchant_id=merchant_id,
                endpoint=endpoint,
                error="API request failed - check credentials and endpoint"
            )
            
    except Exception as e:
        logger.error(f"API test error for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"API test failed: {str(e)}")

@router.get("/health/{merchant_id}")
async def check_api_health(merchant_id: str):
    """
    Check API client health for a merchant
    
    Args:
        merchant_id: Merchant identifier
        
    Returns:
        API health status
    """
    try:
        client = ZidAPIClient(merchant_id)
        is_healthy = await client.health_check()
        
        return {
            "merchant_id": merchant_id,
            "healthy": is_healthy,
            "message": "API client is working" if is_healthy else "API client has issues"
        }
        
    except Exception as e:
        logger.error(f"API health check failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/validate-tokens/{merchant_id}")
async def validate_merchant_tokens(merchant_id: str):
    """
    Validate stored tokens for a merchant
    
    Args:
        merchant_id: Merchant identifier
        
    Returns:
        Token validation results
    """
    try:
        client = ZidAPIClient(merchant_id)
        validation_result = await client.validate_tokens()
        
        return TokenValidationResponse(**validation_result)
        
    except Exception as e:
        logger.error(f"Token validation failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token validation failed: {str(e)}")

@router.post("/refresh-tokens/{merchant_id}")
async def refresh_merchant_tokens(merchant_id: str):
    """
    Force refresh tokens for a merchant
    
    Args:
        merchant_id: Merchant identifier
        
    Returns:
        Token refresh results
    """
    try:
        client = ZidAPIClient(merchant_id)
        
        # Force token refresh
        result = await client.oauth_service.refresh_tokens(merchant_id)
        
        return {
            "success": True,
            "merchant_id": merchant_id,
            "message": "Tokens refreshed successfully",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Token refresh failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")

@router.get("/store/{merchant_id}")
async def get_store_info(merchant_id: str):
    """
    Get store information using the API client
    
    Args:
        merchant_id: Merchant identifier
        
    Returns:
        Store information from Zid API
    """
    try:
        client = ZidAPIClient(merchant_id)
        store_data = await client.get("/store")
        
        if store_data:
            return {
                "success": True,
                "merchant_id": merchant_id,
                "store": store_data
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to retrieve store information")
            
    except Exception as e:
        logger.error(f"Store info request failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Store info request failed: {str(e)}")

@router.get("/products/{merchant_id}")
async def get_products(
    merchant_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page")
):
    """
    Get products list using the API client
    
    Args:
        merchant_id: Merchant identifier
        page: Page number
        limit: Items per page
        
    Returns:
        Products list from Zid API
    """
    try:
        client = ZidAPIClient(merchant_id)
        products_data = await client.get("/products", params={"page": page, "limit": limit})
        
        if products_data:
            return {
                "success": True,
                "merchant_id": merchant_id,
                "page": page,
                "limit": limit,
                "products": products_data
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to retrieve products")
            
    except Exception as e:
        logger.error(f"Products request failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Products request failed: {str(e)}")

@router.get("/orders/{merchant_id}")
async def get_orders(
    merchant_id: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page")
):
    """
    Get orders list using the API client
    
    Args:
        merchant_id: Merchant identifier
        page: Page number
        limit: Items per page
        
    Returns:
        Orders list from Zid API
    """
    try:
        client = ZidAPIClient(merchant_id)
        orders_data = await client.get("/orders", params={"page": page, "limit": limit})
        
        if orders_data:
            return {
                "success": True,
                "merchant_id": merchant_id,
                "page": page,
                "limit": limit,
                "orders": orders_data
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to retrieve orders")
            
    except Exception as e:
        logger.error(f"Orders request failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Orders request failed: {str(e)}")