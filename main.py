"""
Main entry point for the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes import router as api_router
from services.whatsapp_service import router as whatsapp_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup: Log available routes
    logger.info("Available routes:")
    for route in app.routes:
        logger.info(f"- {route.path} [{','.join(route.methods)}]")
    yield
    # Shutdown: Add any cleanup here if needed
    logger.info("Shutting down application...")

# Create FastAPI app
app = FastAPI(
    title="AI Diet Coach",
    description="AI-powered diet coaching via WhatsApp",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(whatsapp_router, tags=["whatsapp"])
