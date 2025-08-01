from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging

from ..api.zid_client import ZidAPIClient
from ..models.database import ZidCredential, OAuthState, TokenAuditLog
from ..database import get_db
from sqlalchemy import select, delete

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

@router.get("/merchants")
async def list_merchants():
    """
    List all stored merchant credentials
    
    Returns:
        List of merchants with their credential status
    """
    try:
        async with get_db() as db:
            stmt = select(ZidCredential)
            result = await db.execute(stmt)
            credentials = result.scalars().all()
            
            merchants = []
            for cred in credentials:
                merchants.append({
                    "merchant_id": cred.merchant_id,
                    "credential_id": cred.id,
                    "is_active": cred.is_active,
                    "expires_at": cred.expires_at.isoformat() if cred.expires_at else None,
                    "created_at": cred.created_at.isoformat() if cred.created_at else None,
                    "updated_at": cred.updated_at.isoformat() if cred.updated_at else None
                })
            
            return {
                "total_merchants": len(merchants),
                "merchants": merchants
            }
            
    except Exception as e:
        logger.error(f"Failed to list merchants: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list merchants: {str(e)}")

@router.delete("/merchants/{merchant_id}")
async def delete_merchant(merchant_id: str):
    """
    Delete a merchant and all associated data
    
    Args:
        merchant_id: Merchant identifier to delete
        
    Returns:
        Deletion confirmation
    """
    try:
        async with get_db() as db:
            # Find the merchant credential
            stmt = select(ZidCredential).where(ZidCredential.merchant_id == merchant_id)
            result = await db.execute(stmt)
            credential = result.scalar_one_or_none()
            
            if not credential:
                raise HTTPException(status_code=404, detail=f"Merchant {merchant_id} not found")
            
            # Delete associated audit logs
            audit_stmt = delete(TokenAuditLog).where(TokenAuditLog.merchant_id == merchant_id)
            await db.execute(audit_stmt)
            
            # Delete the credential
            await db.delete(credential)
            await db.commit()
            
            logger.info(f"Deleted merchant {merchant_id} and all associated data")
            
            return {
                "success": True,
                "merchant_id": merchant_id,
                "message": "Merchant and all associated data deleted successfully"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete merchant: {str(e)}")

@router.delete("/cleanup")
async def cleanup_old_data():
    """
    Clean up old OAuth states and expired data
    
    Returns:
        Cleanup results
    """
    try:
        from datetime import datetime
        
        async with get_db() as db:
            # Delete old/expired OAuth states
            oauth_stmt = delete(OAuthState).where(
                OAuthState.expires_at < datetime.utcnow()
            )
            oauth_result = await db.execute(oauth_stmt)
            
            await db.commit()
            
            cleanup_result = {
                "success": True,
                "expired_oauth_states_deleted": oauth_result.rowcount,
                "message": "Cleanup completed successfully"
            }
            
            logger.info(f"Cleanup completed: {cleanup_result}")
            return cleanup_result
            
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@router.get("/products/{merchant_id}")
async def get_products(merchant_id: str, page: int = 1, limit: int = 10, search: Optional[str] = None):
    """
    Retrieve a list of products for the given merchant.

    This endpoint calls the Zid API using stored credentials and returns a paginated list
    of products. Optional filtering by `attribute_values` is supported.

    Args:
        merchant_id: The merchant identifier
        page: Page number for pagination (default: 1)
        limit: Items per page (default: 10, max: 50)
        search: Optional comma-separated attribute filters (e.g. "nike,black,large")

    Returns:
        List of products, pagination metadata, and API response fields

    Zid API Reference:
    https://developer.zid.sa/docs/apis/products#get-products

    Required Headers (auto-injected):
        - Authorization: Bearer {partner_token}
        - Access-Token: {merchant_token}
        - Store-Id: {store_id}
        - Role: Manager
        - Accept-Language: all-languages
        - User-Agent: ZidIntegration/1.0.0 (Merchant: {merchant_id})
    """
    try:
        client = ZidAPIClient(merchant_id)
        params = {
            "page": page,
            "page_size": min(limit, 50),
        }
        if search:
            params["attribute_values"] = search

        response = await client.get("/products/", params=params)

        return {
            "success": True,
            "merchant_id": merchant_id,
            "products": response.get("results", []),
            "count": response.get("count"),
            "next": response.get("next"),
            "previous": response.get("previous")
        }
    except Exception as e:
        logger.error(f"Failed to get products for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Products request failed")

@router.get("/orders/{merchant_id}")
async def get_orders(
    merchant_id: str,
    # Pagination
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    # Status filtering
    status: Optional[str] = Query(default=None, description="Filter by order status: pending, confirmed, shipped, delivered, cancelled"),
    payment_status: Optional[str] = Query(default=None, description="Filter by payment status"),
    fulfillment_status: Optional[str] = Query(default=None, description="Filter by fulfillment status"),
    # Date filtering
    date_from: Optional[str] = Query(default=None, description="Start date filter (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(default=None, description="End date filter (YYYY-MM-DD)"),
    date_field: str = Query(default="created_at", description="Date field to filter by: created_at, updated_at, shipped_at"),
    # Customer filtering
    customer_id: Optional[int] = Query(default=None, description="Filter by customer ID"),
    customer_email: Optional[str] = Query(default=None, description="Filter by customer email"),
    customer_phone: Optional[str] = Query(default=None, description="Filter by customer phone"),
    # Amount filtering
    min_amount: Optional[float] = Query(default=None, ge=0, description="Minimum order amount"),
    max_amount: Optional[float] = Query(default=None, ge=0, description="Maximum order amount"),
    # Search
    search: Optional[str] = Query(default=None, description="Search in order number, customer name, or products"),
    order_number: Optional[str] = Query(default=None, description="Search by specific order number"),
    # Sorting
    sort_by: str = Query(default="created_at", description="Sort by: created_at, updated_at, total_amount, order_number"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order: asc or desc")
):
    """
    Get orders list with comprehensive filtering and search capabilities
    
    Args:
        merchant_id: Merchant identifier
        page: Page number for pagination
        limit: Items per page (max 100)
        status: Filter by order status
        payment_status: Filter by payment status
        fulfillment_status: Filter by fulfillment status
        date_from/date_to: Date range filtering
        date_field: Which date field to use for filtering
        customer_id/email/phone: Customer filtering options
        min_amount/max_amount: Order amount range
        search: Text search across order data
        order_number: Specific order lookup
        sort_by: Field to sort by
        sort_order: Sorting direction
        
    Returns:
        Enhanced orders list with metadata from Zid API
    """
    try:
        client = ZidAPIClient(merchant_id)
        
        # Build query parameters for Zid API
        params = {
            "page": page,
            "per_page": limit,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        # Add filtering parameters
        if status:
            params["status"] = status
        if payment_status:
            params["payment_status"] = payment_status
        if fulfillment_status:
            params["fulfillment_status"] = fulfillment_status
        if date_from:
            params[f"{date_field}_from"] = date_from
        if date_to:
            params[f"{date_field}_to"] = date_to
        if customer_id is not None:
            params["customer_id"] = customer_id
        if customer_email:
            params["customer_email"] = customer_email
        if customer_phone:
            params["customer_phone"] = customer_phone
        if min_amount is not None:
            params["min_amount"] = min_amount
        if max_amount is not None:
            params["max_amount"] = max_amount
        if search:
            params["search"] = search
        if order_number:
            params["order_number"] = order_number
        
        logger.info(f"Fetching orders for merchant {merchant_id} with filters: {params}")
        
        # Make request to Zid API
        orders_data = await client.get("/v1/managers/orders", params=params)
        
        if orders_data:
            # Extract pagination info from response
            total_count = orders_data.get("total_orders_count", 0)
            orders_list = orders_data.get("orders", [])
            
            # Build enhanced response
            response = {
                "success": True,
                "merchant_id": merchant_id,
                "orders": orders_list,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0,
                    "has_next": page * limit < total_count,
                    "has_prev": page > 1
                },
                "filters_applied": {
                    "status": status,
                    "payment_status": payment_status,
                    "fulfillment_status": fulfillment_status,
                    "date_range": {
                        "field": date_field,
                        "from": date_from,
                        "to": date_to
                    } if date_from or date_to else None,
                    "customer": {
                        "id": customer_id,
                        "email": customer_email,
                        "phone": customer_phone
                    } if customer_id or customer_email or customer_phone else None,
                    "amount_range": {"min": min_amount, "max": max_amount} if min_amount or max_amount else None,
                    "search": search,
                    "order_number": order_number
                },
                "sorting": {
                    "sort_by": sort_by,
                    "sort_order": sort_order
                },
                "metadata": {
                    "results_count": len(orders_list),
                    "total_orders": total_count
                }
            }
            
            logger.info(f"Orders retrieved successfully for merchant {merchant_id}: {len(orders_list)} items")
            return response
            
        else:
            raise HTTPException(status_code=400, detail="Failed to retrieve orders")
            
    except Exception as e:
        logger.error(f"Orders request failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Orders request failed: {str(e)}")

@router.get("/products/{merchant_id}/{product_id}")
async def get_product_by_id(merchant_id: str, product_id: str):
    """
    Get a single product by ID with complete details
    
    Args:
        merchant_id: Merchant identifier
        product_id: Product unique identifier
        
    Returns:
        Complete product information from Zid API
    """
    try:
        client = ZidAPIClient(merchant_id)
        
        logger.info(f"Fetching product {product_id} for merchant {merchant_id}")
        
        # Get product details from Zid API
        product_data = await client.get(f"/v1/managers/store/products/{product_id}")
        
        if product_data:
            response = {
                "success": True,
                "merchant_id": merchant_id,
                "product_id": product_id,
                "product": product_data.get("product", product_data)
            }
            
            logger.info(f"Product {product_id} retrieved successfully for merchant {merchant_id}")
            return response
            
        else:
            raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
            
    except Exception as e:
        logger.error(f"Product {product_id} request failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Product request failed: {str(e)}")

@router.get("/orders/{merchant_id}/{order_id}")
async def get_order_by_id(merchant_id: str, order_id: str):
    """
    Get a single order by ID with complete details
    
    Args:
        merchant_id: Merchant identifier
        order_id: Order unique identifier
        
    Returns:
        Complete order information from Zid API
    """
    try:
        client = ZidAPIClient(merchant_id)
        
        logger.info(f"Fetching order {order_id} for merchant {merchant_id}")
        
        # Get order details from Zid API
        order_data = await client.get(f"/v1/managers/orders/{order_id}")
        
        if order_data:
            response = {
                "success": True,
                "merchant_id": merchant_id,
                "order_id": order_id,
                "order": order_data.get("order", order_data)
            }
            
            logger.info(f"Order {order_id} retrieved successfully for merchant {merchant_id}")
            return response
            
        else:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
            
    except Exception as e:
        logger.error(f"Order {order_id} request failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Order request failed: {str(e)}")

@router.get("/customers/{merchant_id}")
async def get_customers(
    merchant_id: str,
    # Pagination
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    # Search and filtering
    search: Optional[str] = Query(default=None, description="Search in customer name, email, or phone"),
    email: Optional[str] = Query(default=None, description="Filter by email"),
    phone: Optional[str] = Query(default=None, description="Filter by phone number"),
    status: Optional[str] = Query(default=None, description="Filter by customer status"),
    # Date filtering
    registered_from: Optional[str] = Query(default=None, description="Customer registration start date (YYYY-MM-DD)"),
    registered_to: Optional[str] = Query(default=None, description="Customer registration end date (YYYY-MM-DD)"),
    # Sorting
    sort_by: str = Query(default="created_at", description="Sort by: created_at, updated_at, name, email"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$", description="Sort order: asc or desc")
):
    """
    Get customers list with filtering and search capabilities
    
    Args:
        merchant_id: Merchant identifier
        page: Page number for pagination
        limit: Items per page (max 100)
        search: Text search in customer data
        email/phone: Specific customer lookup
        status: Filter by customer status
        registered_from/to: Registration date range
        sort_by: Field to sort by
        sort_order: Sorting direction
        
    Returns:
        Customers list with metadata from Zid API
    """
    try:
        client = ZidAPIClient(merchant_id)
        
        # Build query parameters for Zid API
        params = {
            "page": page,
            "per_page": limit,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        # Add filtering parameters
        if search:
            params["search"] = search
        if email:
            params["email"] = email
        if phone:
            params["phone"] = phone
        if status:
            params["status"] = status
        if registered_from:
            params["registered_from"] = registered_from
        if registered_to:
            params["registered_to"] = registered_to
        
        logger.info(f"Fetching customers for merchant {merchant_id} with filters: {params}")
        
        # Make request to Zid API
        customers_data = await client.get("/v1/managers/customers", params=params)
        
        if customers_data:
            # Extract pagination info from response
            total_count = customers_data.get("total_customers_count", 0)
            customers_list = customers_data.get("customers", [])
            
            # Build enhanced response
            response = {
                "success": True,
                "merchant_id": merchant_id,
                "customers": customers_list,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0,
                    "has_next": page * limit < total_count,
                    "has_prev": page > 1
                },
                "filters_applied": {
                    "search": search,
                    "email": email,
                    "phone": phone,
                    "status": status,
                    "registration_date_range": {
                        "from": registered_from,
                        "to": registered_to
                    } if registered_from or registered_to else None
                },
                "sorting": {
                    "sort_by": sort_by,
                    "sort_order": sort_order
                },
                "metadata": {
                    "results_count": len(customers_list),
                    "total_customers": total_count
                }
            }
            
            logger.info(f"Customers retrieved successfully for merchant {merchant_id}: {len(customers_list)} items")
            return response
            
        else:
            raise HTTPException(status_code=400, detail="Failed to retrieve customers")
            
    except Exception as e:
        logger.error(f"Customers request failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Customers request failed: {str(e)}")

@router.get("/categories/{merchant_id}")
async def get_categories(
    merchant_id: str,
    # Pagination
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=200, description="Items per page"),
    # Search and filtering
    search: Optional[str] = Query(default=None, description="Search in category name or description"),
    parent_id: Optional[str] = Query(default=None, description="Filter by parent category ID"),
    level: Optional[int] = Query(default=None, ge=0, le=5, description="Filter by category level/depth"),
    status: Optional[str] = Query(default=None, description="Filter by category status"),
    # Sorting
    sort_by: str = Query(default="name", description="Sort by: name, created_at, updated_at, sort_order"),
    sort_order: str = Query(default="asc", regex="^(asc|desc)$", description="Sort order: asc or desc"),
    # Structure options
    include_children: bool = Query(default=False, description="Include child categories in response"),
    flat_structure: bool = Query(default=True, description="Return flat list vs hierarchical structure")
):
    """
    Get product categories list with hierarchical support
    
    Args:
        merchant_id: Merchant identifier
        page: Page number for pagination
        limit: Items per page (max 200)
        search: Text search in category data
        parent_id: Filter by parent category
        level: Filter by category depth level
        status: Filter by category status
        sort_by: Field to sort by
        sort_order: Sorting direction
        include_children: Include child categories
        flat_structure: Return flat vs hierarchical
        
    Returns:
        Categories list with metadata from Zid API
    """
    try:
        client = ZidAPIClient(merchant_id)
        
        # Build query parameters for Zid API
        params = {
            "page": page,
            "per_page": limit,
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        # Add filtering parameters
        if search:
            params["search"] = search
        if parent_id:
            params["parent_id"] = parent_id
        if level is not None:
            params["level"] = level
        if status:
            params["status"] = status
        if include_children:
            params["include_children"] = "true"
        if not flat_structure:
            params["hierarchical"] = "true"
        
        logger.info(f"Fetching categories for merchant {merchant_id} with filters: {params}")
        
        # Make request to Zid API
        categories_data = await client.get("/v1/managers/store/categories", params=params)
        
        if categories_data:
            # Extract pagination info from response
            total_count = categories_data.get("total_categories_count", 0)
            categories_list = categories_data.get("categories", [])
            
            # Build enhanced response
            response = {
                "success": True,
                "merchant_id": merchant_id,
                "categories": categories_list,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_count": total_count,
                    "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0,
                    "has_next": page * limit < total_count,
                    "has_prev": page > 1
                },
                "filters_applied": {
                    "search": search,
                    "parent_id": parent_id,
                    "level": level,
                    "status": status
                },
                "sorting": {
                    "sort_by": sort_by,
                    "sort_order": sort_order
                },
                "structure_options": {
                    "include_children": include_children,
                    "flat_structure": flat_structure
                },
                "metadata": {
                    "results_count": len(categories_list),
                    "total_categories": total_count
                }
            }
            
            logger.info(f"Categories retrieved successfully for merchant {merchant_id}: {len(categories_list)} items")
            return response
            
        else:
            raise HTTPException(status_code=400, detail="Failed to retrieve categories")
            
    except Exception as e:
        logger.error(f"Categories request failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Categories request failed: {str(e)}")

@router.get("/customers/{merchant_id}/{customer_id}")
async def get_customer_by_id(merchant_id: str, customer_id: str):
    """
    Get a single customer by ID with complete details
    
    Args:
        merchant_id: Merchant identifier
        customer_id: Customer unique identifier
        
    Returns:
        Complete customer information from Zid API
    """
    try:
        client = ZidAPIClient(merchant_id)
        
        logger.info(f"Fetching customer {customer_id} for merchant {merchant_id}")
        
        # Get customer details from Zid API
        customer_data = await client.get(f"/v1/managers/customers/{customer_id}")
        
        if customer_data:
            response = {
                "success": True,
                "merchant_id": merchant_id,
                "customer_id": customer_id,
                "customer": customer_data.get("customer", customer_data)
            }
            
            logger.info(f"Customer {customer_id} retrieved successfully for merchant {merchant_id}")
            return response
            
        else:
            raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
            
    except Exception as e:
        logger.error(f"Customer {customer_id} request failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Customer request failed: {str(e)}")

@router.get("/categories/{merchant_id}/{category_id}")
async def get_category_by_id(
    merchant_id: str, 
    category_id: str,
    include_children: bool = Query(default=False, description="Include child categories in response"),
    include_products: bool = Query(default=False, description="Include products in this category")
):
    """
    Get a single category by ID with complete details
    
    Args:
        merchant_id: Merchant identifier
        category_id: Category unique identifier
        include_children: Include child categories
        include_products: Include products in category
        
    Returns:
        Complete category information from Zid API
    """
    try:
        client = ZidAPIClient(merchant_id)
        
        # Build query parameters
        params = {}
        if include_children:
            params["include_children"] = "true"
        if include_products:
            params["include_products"] = "true"
        
        logger.info(f"Fetching category {category_id} for merchant {merchant_id} with params: {params}")
        
        # Get category details from Zid API
        category_data = await client.get(f"/v1/managers/store/categories/{category_id}", params=params)
        
        if category_data:
            response = {
                "success": True,
                "merchant_id": merchant_id,
                "category_id": category_id,
                "category": category_data.get("category", category_data),
                "options": {
                    "include_children": include_children,
                    "include_products": include_products
                }
            }
            
            logger.info(f"Category {category_id} retrieved successfully for merchant {merchant_id}")
            return response
            
        else:
            raise HTTPException(status_code=404, detail=f"Category {category_id} not found")
            
    except Exception as e:
        logger.error(f"Category {category_id} request failed for merchant {merchant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Category request failed: {str(e)}")