"""
Service for handling webhook requests and integrating with the chat service.
"""

import logging
from typing import Dict, Any, Optional, Tuple, List
from services.chat_service import chat_service

logger = logging.getLogger(__name__)

class WebhookService:
    def extract_whatsapp_message(self, data: Dict[str, Any]) -> List[Tuple[str, str]]:
        """
        Extract messages from WhatsApp webhook payload.
        
        Args:
            data: The webhook payload from WhatsApp
            
        Returns:
            List[Tuple[str, str]]: List of (user_id, message) tuples
        """
        messages = []
        try:
            # Handle WhatsApp webhook format
            if "entry" in data:
                for entry in data["entry"]:
                    if "changes" in entry:
                        for change in entry["changes"]:
                            if change.get("value", {}).get("messages"):
                                for message in change["value"]["messages"]:
                                    if message.get("type") == "text":
                                        user_id = message.get("from")
                                        text = message.get("text", {}).get("body", "")
                                        if user_id and text:
                                            messages.append((user_id, text))
            return messages
        except Exception as e:
            logger.error(f"Error extracting WhatsApp message: {e}", exc_info=True)
            return []

    async def process_webhook(
        self,
        data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Process an incoming webhook request.
        
        Args:
            data: The webhook payload
            
        Returns:
            List[Dict[str, Any]]: List of responses for each processed message
        """
        try:
            responses = []
            
            # Extract messages from WhatsApp format
            messages = self.extract_whatsapp_message(data)
            
            # Process each message
            for user_id, message in messages:
                try:
                    # Process the message using the chat service
                    response, profile_data = await chat_service.process_message(
                        user_id=user_id,
                        message=message
                    )
                    
                    responses.append({
                        "status": "success",
                        "response": response,
                        "profile": profile_data,
                        "user_id": user_id
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing message for user {user_id}: {e}", exc_info=True)
                    responses.append({
                        "status": "error",
                        "error": str(e),
                        "user_id": user_id
                    })
            
            return responses
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            raise

# Create a single instance
webhook_service = WebhookService() 