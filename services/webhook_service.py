"""
Service for handling WhatsApp webhook events.
"""

import logging
import os
import json
from typing import Dict, Any
from uuid import uuid4
from datetime import datetime

from fastapi import APIRouter, Request, Response
from services.chat_service import chat_service

logger = logging.getLogger(__name__)

class WebhookService:
    def __init__(self):
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        if not self.verify_token:
            raise ValueError("WHATSAPP_VERIFY_TOKEN is required")
        
        self.router = APIRouter()
        self._setup_routes()
        
    def _setup_routes(self):
        @self.router.get("/webhook")
        async def verify_webhook(request: Request):
            """
            Verify webhook endpoint for WhatsApp API.
            """
            try:
                # Get query parameters
                params = dict(request.query_params)
                logger.info(f"Webhook verification request params: {params}")
                
                # Extract verification parameters
                mode = params.get("hub.mode")
                token = params.get("hub.verify_token")
                challenge = params.get("hub.challenge")
                
                # Verify token
                if mode == "subscribe" and token == self.verify_token:
                    if not challenge:
                        raise ValueError("Missing hub.challenge")
                    logger.info("Webhook verified successfully")
                    return Response(content=challenge, media_type="text/plain")
                    
                raise ValueError("Invalid verification token")
                
            except ValueError as e:
                logger.error(f"Invalid challenge format: {e}")
                raise ValueError("Invalid challenge format")
            except Exception as e:
                logger.error(f"Webhook verification failed: {e}")
                raise ValueError("Webhook verification failed")

        @self.router.post("/webhook")
        async def handle_webhook(request: Request) -> Dict[str, Any]:
            """
            Handle incoming webhook events from WhatsApp.
            """
            try:
                data = await request.json()
                logger.debug(f"Received webhook data: {json.dumps(data, indent=2)}")
                
                # Extract message details
                entry = data.get("entry", [{}])[0]
                changes = entry.get("changes", [{}])[0]
                value = changes.get("value", {})
                
                # Handle message events
                if "messages" in value:
                    message = value["messages"][0]
                    contact = value.get("contacts", [{}])[0]
                    
                    # Extract user info
                    phone_number = contact.get("wa_id")
                    if not phone_number:
                        logger.error("No phone number found in webhook data")
                        return {"status": "error", "message": "No phone number found"}
                        
                    user_id = f"wa_{phone_number}"
                    
                    # Extract message content
                    message_type = message.get("type", "")
                    if message_type != "text":
                        logger.warning(f"Unsupported message type: {message_type}")
                        return {"status": "error", "message": "Unsupported message type"}
                        
                    text = message.get("text", {}).get("body", "").strip()
                    if not text:
                        logger.warning("Empty message received")
                        return {"status": "error", "message": "Empty message"}
                        
                    # Generate a unique message ID
                    message_id = message.get("id", str(uuid4()))
                    
                    # Log the incoming message
                    logger.info(f"Processing message from {user_id}: {text}")
                    
                    try:
                        # Process the message
                        response = await chat_service.process_message(
                            user_id=user_id,
                            message_text=text,
                            message_id=message_id
                        )
                        
                        return {
                            "status": "success",
                            "message": "Message processed successfully",
                            "response": response
                        }
                        
                    except Exception as e:
                        logger.error(f"Error processing message from {user_id}: {e}", exc_info=True)
                        return {
                            "status": "error",
                            "message": "Error processing message",
                            "error": str(e)
                        }
                        
                # Handle verification requests
                elif "challenge" in data:
                    challenge = data["challenge"]
                    return Response(content=challenge, media_type="text/plain")
                    
                return {"status": "success", "message": "Webhook received"}
                
            except Exception as e:
                logger.error(f"Error processing webhook: {e}", exc_info=True)
                return {"status": "error", "message": str(e)}

# Create a single instance
webhook_service = WebhookService()
# Export both the service instance and the router
router = webhook_service.router 