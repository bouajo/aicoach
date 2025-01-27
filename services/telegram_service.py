"""
Service for handling Telegram user account interactions.
"""

import os
import logging
from typing import Dict, Any, Optional
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from data.database import db
from services.chat_service import chat_service

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        """Initialize Telegram service."""
        try:
            # Get credentials from environment
            api_id = os.getenv("TELEGRAM_API_ID")
            api_hash = os.getenv("TELEGRAM_API_HASH")
            phone_number = os.getenv("TELEGRAM_PHONE_NUMBER")
            session_string = os.getenv("TELETHON_SESSION")

            if not all([api_id, api_hash, phone_number, session_string]):
                raise ValueError("Missing Telegram credentials")

            # Initialize client with session string
            self.client = TelegramClient(
                StringSession(session_string),
                int(api_id),
                api_hash
            )
            self.phone_number = phone_number

            # Register message handler
            @self.client.on(events.NewMessage)
            async def handle_message(event):
                # Ignore messages from ourselves
                if event.message.out:
                    return
                await self.handle_message(event)

            logger.info("Starting Telegram user client...")

        except Exception as e:
            logger.error(f"Error initializing Telegram service: {str(e)}")
            raise

    async def handle_message(self, event):
        """Handle incoming Telegram messages."""
        try:
            # Get user info
            user_id = str(event.sender_id)
            message = event.message.text

            # Get or create user data
            user_data = await self._get_or_create_user(user_id)
            
            # Process message
            response, _ = await chat_service.process_message(
                user_id=user_id,
                message=message,
                user_data=user_data
            )

            # Send response
            await event.reply(response)

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            await event.reply("Désolé, j'ai rencontré une erreur. Veuillez réessayer.")

    async def _get_or_create_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get or create user data."""
        try:
            # Try to get existing user
            user_data = await db.get_user_profile(user_id)
            if user_data:
                return user_data

            # Create new user profile
            profile_data = {
                "user_id": user_id,
                "language": "français"
            }
            await db.update_user_profile(user_id, profile_data)
            return profile_data

        except Exception as e:
            logger.error(f"Error getting/creating user: {str(e)}")
            return None

    async def start(self):
        """Start the Telegram client."""
        await self.client.start(phone=self.phone_number)
        await self.client.run_until_disconnected()

# Global Telegram service instance
telegram_service = TelegramService() 