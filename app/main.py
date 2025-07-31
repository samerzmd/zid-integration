from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from contextlib import asynccontextmanager

from .config import settings
from .database import init_db, close_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    logger.info("Starting Zid Integration Service...")
    
    # Run database migrations
    try:
        import subprocess
        logger.info("Running database migrations...")
        result = subprocess.run(["alembic", "upgrade", "head"], 
                              capture_output=True, text=True, cwd=".")
        if result.returncode != 0:
            logger.error(f"Migration failed: {result.stderr}")
            raise Exception(f"Database migration failed: {result.stderr}")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Failed to run migrations: {str(e)}")
        # Don't fail startup - try to initialize tables directly
        await init_db()
        logger.info("Database initialized with direct table creation")
    
    yield
    
    logger.info("Shutting down Zid Integration Service...")
    await close_db()

app = FastAPI(
    title="Zid Integration Service",
    description="OAuth 2.0 authentication and API integration service for Zid e-commerce platform",
    version="1.0.0",
    lifespan=lifespan
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # TODO: Configure for production
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from .routers import auth, api
app.include_router(auth.router)
app.include_router(api.router)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Zid Integration Service",
        "version": "1.0.0",
        "status": "active",
        "phase": "Phase 1 Complete - Ready for Phase 2",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "auth": "/auth",
            "api": "/api"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and DigitalOcean"""
    return {
        "status": "healthy",
        "service": "zid-integration-service",
        "phase": "infrastructure-ready"
    }

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=os.getenv("ENV") == "development"
    )