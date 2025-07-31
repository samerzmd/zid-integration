from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """Application configuration with environment variable support"""
    
    # Database Configuration
    database_url: str = "postgresql+asyncpg://zid_user:zid_password@localhost:5433/zid_db"
    
    # Redis Configuration  
    redis_url: str = "redis://localhost:6379/0"
    
    # Zid OAuth Configuration
    zid_client_id: Optional[str] = None
    zid_client_secret: Optional[str] = None
    zid_redirect_uri: str = "http://localhost:8000/auth/callback"
    
    # Security
    encryption_key: str  # Required - 32 byte base64 encoded key
    
    # Application Settings
    env: str = "development"
    port: int = 8000
    host: str = "0.0.0.0"
    
    # Logging
    log_level: str = "INFO"
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # OAuth Settings
    oauth_state_expiry_minutes: int = 10
    token_refresh_buffer_minutes: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()