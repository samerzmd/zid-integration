from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any, Dict


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str


class MerchantTokenCreate(BaseModel):
    merchant_id: str
    access_token: str
    refresh_token: str
    expires_in: int


class MerchantTokenResponse(BaseModel):
    id: int
    merchant_id: str
    expires_in: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WebhookEventCreate(BaseModel):
    event_type: str
    event_id: str
    merchant_id: str
    payload: Dict[str, Any]


class WebhookEventResponse(BaseModel):
    id: int
    event_type: str
    event_id: str
    merchant_id: str
    payload: Dict[str, Any]
    processed: bool
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    status: str


class StockResponse(BaseModel):
    product_id: int
    quantity: int
    location: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    status: str
    total: float
    created_at: str
    customer_name: Optional[str] = None


class PriceUpdateRequest(BaseModel):
    price: float


class HealthResponse(BaseModel):
    status: str