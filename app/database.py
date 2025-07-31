from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings

# Convert PostgreSQL URL to async format for asyncpg
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
else:
    async_database_url = database_url

# Handle SSL parameters for asyncpg
if "sslmode=" in async_database_url:
    # Replace sslmode with ssl for asyncpg compatibility
    async_database_url = async_database_url.replace("sslmode=require", "ssl=true")
    async_database_url = async_database_url.replace("sslmode=prefer", "ssl=true")
    async_database_url = async_database_url.replace("sslmode=disable", "ssl=false")

# Create async engine for PostgreSQL
engine = create_async_engine(
    async_database_url, 
    echo=not settings.is_production,  # Disable SQL logging in production
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()