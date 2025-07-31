from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    database_url: str
    zid_client_id: str
    zid_client_secret: str
    zid_redirect_uri: str
    zid_api_base_url: str = "https://api.zid.sa"
    secret_key: str
    
    # Production settings
    environment: str = "development"
    cors_origins: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


settings = Settings()