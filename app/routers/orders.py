from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..database import get_db
from ..auth import AuthService
from ..zid_client import ZidAPIClient
from ..schemas import OrderResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])


async def get_authenticated_client(
    merchant_id: str,
    db: AsyncSession = Depends(get_db)
) -> ZidAPIClient:
    """Get authenticated Zid API client for a merchant"""
    auth_service = AuthService(db)
    try:
        access_token = await auth_service.get_valid_token(merchant_id)
        return ZidAPIClient(access_token=access_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


@router.get("/", response_model=List[OrderResponse])
async def get_orders(
    merchant_id: str = Query(..., description="Merchant ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get latest orders for a merchant (defaults to latest 20)"""
    client = await get_authenticated_client(merchant_id, db)
    
    try:
        response = await client.get_orders(page=page, page_size=page_size)
        
        # Transform response to match our schema
        orders = []
        if "orders" in response:
            for order_data in response["orders"]:
                order = OrderResponse(
                    id=order_data.get("id"),
                    status=order_data.get("status", "unknown"),
                    total=float(order_data.get("total", 0)),
                    created_at=order_data.get("created_at", ""),
                    customer_name=order_data.get("customer", {}).get("name")
                )
                orders.append(order)
        
        return orders
    
    except Exception as e:
        logger.error(f"Error fetching orders for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")
    
    finally:
        await client.close()