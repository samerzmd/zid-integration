from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
from ..database import get_db
from ..models import WebhookEvent
from ..schemas import WebhookEventCreate, WebhookEventResponse
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def validate_webhook_signature(
    request: Request,
    signature: Optional[str] = Header(None, alias="X-Zid-Signature"),
    timestamp: Optional[str] = Header(None, alias="X-Zid-Timestamp")
) -> bool:
    """Validate webhook signature (implement based on Zid's webhook security)"""
    # TODO: Implement actual signature validation based on Zid's webhook documentation
    # For now, we'll just log the headers for debugging
    logger.info(f"Webhook signature: {signature}")
    logger.info(f"Webhook timestamp: {timestamp}")
    return True


@router.post("/zid")
async def handle_zid_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle incoming webhooks from Zid"""
    try:
        # Get request body
        body = await request.body()
        payload = json.loads(body.decode())
        
        # Validate webhook (implement signature validation as needed)
        # is_valid = await validate_webhook_signature(request)
        # if not is_valid:
        #     raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Extract event information
        event_type = payload.get("event", "unknown")
        event_id = payload.get("id", f"webhook_{datetime.utcnow().timestamp()}")
        merchant_id = payload.get("merchant_id", payload.get("store_id", "unknown"))
        
        logger.info(f"Received webhook: {event_type} for merchant: {merchant_id}")
        
        # Create webhook event record
        webhook_event = WebhookEventCreate(
            event_type=event_type,
            event_id=str(event_id),
            merchant_id=str(merchant_id),
            payload=payload
        )
        
        # Save to database
        db_event = WebhookEvent(**webhook_event.dict())
        db.add(db_event)
        await db.commit()
        await db.refresh(db_event)
        
        # Process the webhook based on event type
        await process_webhook_event(db_event, db)
        
        logger.info(f"Webhook {event_type} processed successfully")
        return {"status": "success", "message": "Webhook processed successfully"}
    
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


async def process_webhook_event(event: WebhookEvent, db: AsyncSession):
    """Process webhook event based on type"""
    try:
        if event.event_type == "order.created":
            await handle_order_created(event, db)
        elif event.event_type == "order.updated":
            await handle_order_updated(event, db)
        elif event.event_type == "product.updated":
            await handle_product_updated(event, db)
        elif event.event_type == "product.stock.updated":
            await handle_product_stock_updated(event, db)
        else:
            logger.info(f"Unhandled webhook event type: {event.event_type}")
        
        # Mark event as processed
        event.processed = True
        event.processed_at = datetime.utcnow()
        await db.commit()
        
    except Exception as e:
        logger.error(f"Error processing webhook event {event.id}: {str(e)}")
        raise


async def handle_order_created(event: WebhookEvent, db: AsyncSession):
    """Handle order.created webhook event"""
    order_data = event.payload
    logger.info(f"Processing order.created for order ID: {order_data.get('id')}")
    
    # Implement your order created logic here
    # For example:
    # - Send confirmation email
    # - Update inventory
    # - Trigger fulfillment process
    # - Update analytics


async def handle_order_updated(event: WebhookEvent, db: AsyncSession):
    """Handle order.updated webhook event"""
    order_data = event.payload
    logger.info(f"Processing order.updated for order ID: {order_data.get('id')}")
    
    # Implement your order updated logic here
    # For example:
    # - Update order status in local database
    # - Send status update notifications
    # - Trigger shipping updates


async def handle_product_updated(event: WebhookEvent, db: AsyncSession):
    """Handle product.updated webhook event"""
    product_data = event.payload
    logger.info(f"Processing product.updated for product ID: {product_data.get('id')}")
    
    # Implement your product updated logic here
    # For example:
    # - Update local product cache
    # - Sync with third-party systems
    # - Update search index


async def handle_product_stock_updated(event: WebhookEvent, db: AsyncSession):
    """Handle product.stock.updated webhook event"""
    stock_data = event.payload
    logger.info(f"Processing product.stock.updated for product ID: {stock_data.get('product_id')}")
    
    # Implement your stock updated logic here
    # For example:
    # - Update local inventory
    # - Send low stock alerts
    # - Update availability status


@router.get("/events", response_model=list[WebhookEventResponse])
async def get_webhook_events(
    merchant_id: Optional[str] = None,
    event_type: Optional[str] = None,
    processed: Optional[bool] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get webhook events with optional filtering"""
    from sqlalchemy import select
    
    query = select(WebhookEvent)
    
    if merchant_id:
        query = query.where(WebhookEvent.merchant_id == merchant_id)
    if event_type:
        query = query.where(WebhookEvent.event_type == event_type)
    if processed is not None:
        query = query.where(WebhookEvent.processed == processed)
    
    query = query.limit(limit).order_by(WebhookEvent.created_at.desc())
    result = await db.execute(query)
    events = result.scalars().all()
    return events