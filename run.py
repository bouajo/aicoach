"""
Main application entry point.
"""

from dotenv import load_dotenv
load_dotenv()  # Load environment variables first

import logging
import uvicorn
from fastapi import FastAPI
from services.webhook_service import router as webhook_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create FastAPI app
app = FastAPI(title="AI Coach API")

# Add routes
app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])

if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
