"""
Main application entry point.
"""

import os
import logging
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from uvicorn import Config, Server
from services.telegram_service import telegram_service
from api.routes import router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()
app.include_router(router)

async def start_services():
    """Start all services."""
    # Start Telegram service
    await telegram_service.start()

def main():
    """Main entry point."""
    try:
        # Create uvicorn config
        config = Config(app=app, host="0.0.0.0", port=8000)
        server = Server(config)

        # Run both FastAPI and Telegram service
        loop = asyncio.get_event_loop()
        loop.create_task(start_services())
        loop.run_until_complete(server.serve())
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}")
        raise

if __name__ == "__main__":
    main()