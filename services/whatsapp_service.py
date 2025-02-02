"""
Service for sending messages via WhatsApp API.
"""

import logging
import os
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        """Initialize WhatsApp service with credentials from environment."""
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.api_version = "v18.0"  # Latest stable version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        if not self.phone_number_id or not self.access_token:
            raise ValueError("WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN are required")
            
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
    async def send_message(self, to: str, message: str) -> bool:
        """
        Send a message to a WhatsApp user.
        
        Args:
            to: Recipient's phone number
            message: Message text to send
            
        Returns:
            bool: True if successful
        """
        try:
            endpoint = f"/{self.phone_number_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": message}
            }
            
            response = await self.client.post(endpoint, json=payload)
            response.raise_for_status()
            
            logger.info(f"Message sent to {to}: {message[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message to {to}: {e}", exc_info=True)
            return False
            
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

# Create a single instance
whatsapp_service = WhatsAppService() 