from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Database engine
# Convert postgresql:// to postgresql+asyncpg:// for async support
# and handle SSL parameters properly for asyncpg
database_url = settings.database_url
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Handle SSL mode for asyncpg - remove sslmode parameter and add ssl='require' as connect_args
connect_args = {}
if "sslmode=require" in database_url:
    database_url = database_url.replace("?sslmode=require", "").replace("&sslmode=require", "")
    connect_args["ssl"] = "require"

engine = create_async_engine(
    database_url,
    echo=settings.env == "development",
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()

@asynccontextmanager
async def get_db():
    """Database session context manager"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_db_session():
    """FastAPI dependency for database sessions"""
    async with get_db() as session:
        yield session

async def init_db():
    """Initialize database tables"""
    try:
        # Import all models to ensure they're registered
        from .models.database import ZidCredential, OAuthState, TokenAuditLog
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

async def close_db():
    """Close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")