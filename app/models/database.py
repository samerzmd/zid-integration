from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from datetime import datetime
import uuid
from ..database import Base

class ZidCredential(Base):
    """Secure storage for Zid OAuth credentials with encryption at rest"""
    __tablename__ = "zid_credentials"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String, nullable=False, unique=True, index=True)
    store_id = Column(Integer, nullable=True, index=True)  # or nullable=False if you’ve backfilled
    
    # Encrypted tokens (stored as base64 encrypted strings)
    access_token = Column(Text, nullable=False)        # For X-MANAGER-TOKEN header
    authorization_token = Column(Text, nullable=False)  # For Authorization Bearer header
    refresh_token = Column(Text, nullable=False)       # For token refresh
    
    # Token metadata
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Database indexes for performance
    __table_args__ = (
        Index('idx_merchant_active', 'merchant_id', 'is_active'),
        Index('idx_expires_at', 'expires_at'),
        Index('idx_zid_credentials_store_id', 'store_id'),
    )

class OAuthState(Base):
    """OAuth state parameter management for security"""
    __tablename__ = "oauth_states"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    state_hash = Column(String, nullable=False, unique=True, index=True)
    merchant_id = Column(String, nullable=False)
    
    # State lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    
    # Database indexes
    __table_args__ = (
        Index('idx_state_expires', 'state_hash', 'expires_at'),
        Index('idx_expires_cleanup', 'expires_at'),
    )

class TokenAuditLog(Base):
    """Comprehensive audit logging for token operations"""
    __tablename__ = "token_audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String, nullable=False, index=True)
    
    # Action tracking
    action = Column(String, nullable=False)  # 'created', 'refreshed', 'revoked', 'expired'
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Request context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Database indexes
    __table_args__ = (
        Index('idx_merchant_timestamp', 'merchant_id', 'timestamp'),
        Index('idx_action_timestamp', 'action', 'timestamp'),
    )