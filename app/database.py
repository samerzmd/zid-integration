from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings

# Convert PostgreSQL URL to async format for asyncpg
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

database_url = settings.database_url
if database_url.startswith("postgresql://"):
    async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
else:
    async_database_url = database_url

# Handle SSL parameters for asyncpg properly
if "sslmode=" in async_database_url:
    parsed = urlparse(async_database_url)
    query_params = parse_qs(parsed.query)
    
    # Remove sslmode parameter and add ssl=require for asyncpg
    if 'sslmode' in query_params:
        del query_params['sslmode']
    
    # Force SSL connection for DigitalOcean managed PostgreSQL
    # asyncpg uses different SSL parameters than psycopg2
    query_params['ssl'] = ['true']
    
    # Reconstruct the URL with ssl=require
    new_query = urlencode(query_params, doseq=True)
    async_database_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

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