"""
Main script to run the application.
This script initializes and starts all necessary services.
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from contextlib import asynccontextmanager
from pydantic import BaseModel
from services.webhook_service import webhook_service
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get WhatsApp verification token
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "secret-token")

# Initialize FastAPI app
app = FastAPI(
    title="AI Coach API",
    description="AI-powered coaching and conversation API",
    version="1.0.0"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting up services...")
    try:
        # Initialize your services here
        # Example: await initialize_services()
        pass
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        sys.exit(1)
        
    yield
    
    # Shutdown
    logger.info("Shutting down services...")
    try:
        # Cleanup your services here
        # Example: await cleanup_services()
        pass
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

app.router.lifespan_context = lifespan

@app.get("/webhook")
async def verify_webhook(
    request: Request,
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None
):
    """
    Handle WhatsApp webhook verification.
    """
    try:
        # Check if this is a verification request
        if hub_mode == "subscribe" and hub_verify_token:
            if hub_verify_token == WHATSAPP_VERIFY_TOKEN:
                logger.info("Webhook verified successfully")
                return Response(content=hub_challenge, media_type="text/plain")
            else:
                logger.warning("Webhook verification failed - token mismatch")
                raise HTTPException(status_code=403, detail="Verification token mismatch")
                
        raise HTTPException(status_code=400, detail="Invalid verification request")
        
    except Exception as e:
        logger.error(f"Error verifying webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook")
async def webhook(request: Request):
    """
    Handle incoming WhatsApp webhook requests.
    """
    try:
        # Get the raw request data
        data = await request.json()
        logger.info(f"Received webhook data: {data}")
        
        # Process the webhook using the service
        responses = await webhook_service.process_webhook(data)
        
        # Return success even if some messages failed (as per WhatsApp requirements)
        return {"status": "success", "responses": responses}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Always return 200 for WhatsApp webhooks
        return {"status": "error", "error": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

def main():
    """Main function to run the application."""
    try:
        # Get configuration from environment
        host = os.getenv("HOST", "0.0.0.0")
        port = int(os.getenv("PORT", "8000"))
        reload = os.getenv("DEBUG", "false").lower() == "true"
        
        # Print startup message
        print("\n🚀 Starting AI Coach API")
        print(f"{'='*50}")
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Debug mode: {'enabled' if reload else 'disabled'}")
        print(f"{'='*50}\n")
        
        # Start the server
        uvicorn.run(
            "run:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
