from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..database import get_db
from ..auth import AuthService
from ..zid_client import ZidAPIClient
from ..schemas import ProductResponse, StockResponse, PriceUpdateRequest
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["products"])


async def get_authenticated_client(
    merchant_id: str,
    db: AsyncSession = Depends(get_db)
) -> ZidAPIClient:
    """Get authenticated Zid API client for a merchant"""
    auth_service = AuthService(db)
    try:
        access_token, authorization_token = await auth_service.get_valid_token(merchant_id)
        return ZidAPIClient(access_token=access_token, authorization_token=authorization_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    merchant_id: str = Query(..., description="Merchant ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get list of products for a merchant"""
    client = await get_authenticated_client(merchant_id, db)
    
    try:
        response = await client.get_products(page=page, page_size=page_size)
        
        # Transform response to match our schema
        products = []
        if "products" in response:
            for product_data in response["products"]:
                product = ProductResponse(
                    id=product_data.get("id"),
                    name=product_data.get("name", ""),
                    price=float(product_data.get("price", 0)),
                    status=product_data.get("status", "unknown")
                )
                products.append(product)
        
        return products
    
    except Exception as e:
        logger.error(f"Error fetching products for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch products: {str(e)}")
    
    finally:
        await client.close()


@router.get("/{product_id}/stock", response_model=List[StockResponse])
async def get_product_stock(
    product_id: int = Path(..., description="Product ID"),
    merchant_id: str = Query(..., description="Merchant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get stock information for a specific product"""
    client = await get_authenticated_client(merchant_id, db)
    
    try:
        response = await client.get_product_stock(product_id)
        
        # Transform response to match our schema
        stocks = []
        if "stocks" in response:
            for stock_data in response["stocks"]:
                stock = StockResponse(
                    product_id=product_id,
                    quantity=stock_data.get("quantity", 0),
                    location=stock_data.get("location", {}).get("name")
                )
                stocks.append(stock)
        
        return stocks
    
    except Exception as e:
        logger.error(f"Error fetching stock for product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch product stock: {str(e)}")
    
    finally:
        await client.close()


@router.patch("/{product_id}/price")
async def update_product_price(
    product_id: int = Path(..., description="Product ID"),
    price_update: PriceUpdateRequest = ...,
    merchant_id: str = Query(..., description="Merchant ID"),
    db: AsyncSession = Depends(get_db)
):
    """Update product price"""
    client = await get_authenticated_client(merchant_id, db)
    
    try:
        response = await client.update_product_price(product_id, price_update.price)
        
        return {
            "message": "Product price updated successfully",
            "product_id": product_id,
            "new_price": price_update.price
        }
    
    except Exception as e:
        logger.error(f"Error updating price for product {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update product price: {str(e)}")
    
    finally:
        await client.close()