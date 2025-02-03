"""
main.py
A simplified FastAPI server for your AI Diet Coach via WhatsApp.
"""

import os
import logging
from pathlib import Path
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

# Ensure .env is loaded from the correct path
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Local imports
from database import db
from agent import process_incoming_message
from services.webhook_service import router as webhook_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Diet Coach")

@app.on_event("startup")
async def startup():
    """Actions to run at server startup."""
    logger.info("AI Diet Coach is starting up...")
    # Log environment variables for debugging (excluding sensitive data)
    logger.info(f"WHATSAPP_VERIFY_TOKEN loaded: {'WHATSAPP_VERIFY_TOKEN' in os.environ}")
    # We could do further initialization here (e.g., pre-cache or checks)

@app.on_event("shutdown")
async def shutdown():
    """Actions to run at server shutdown."""
    logger.info("AI Diet Coach is shutting down...")

# Include the webhook router - this will handle all webhook routes
app.include_router(webhook_router)

# Note: The POST /webhook route is now handled by the webhook_service router
# The duplicate route has been removed to avoid conflicts

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
