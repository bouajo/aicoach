from fastapi import Request, Response, HTTPException, APIRouter
from typing import Dict, Any
import logging
import os
from agent import process_incoming_message
from database import db
import json

# Configure logger for this module
logger = logging.getLogger(__name__)

class WebhookService:
    def __init__(self):
        """Initialize the WebhookService."""
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        if not self.verify_token:
            raise ValueError("WHATSAPP_VERIFY_TOKEN environment variable is required")
        self.router = APIRouter(prefix="")
        self._setup_routes()

    async def handle_webhook_post(self, request: Request) -> Dict[str, Any]:
        """Process incoming webhook POST requests."""
        try:
            body = await request.json()
            logger.info(f"Received webhook data: {body}")

            # Check if this is a valid WhatsApp message
            if "object" not in body or body["object"] != "whatsapp_business_account":
                return {"status": "ignored", "message": "Not a WhatsApp message"}

            # Process each entry
            for entry in body.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" not in value:
                        continue

                    for message in value.get("messages", []):
                        # Extract message details
                        from_number = message.get("from")
                        if message.get("type") != "text":
                            continue
                            
                        text = message.get("text", {}).get("body", "").strip()
                        
                        if not from_number or not text:
                            continue

                        try:
                            # Process the message using the agent
                            response_text = await process_incoming_message(from_number, text)
                            
                            # Send response back to the user
                            await db.send_whatsapp_message(to=from_number, text=response_text)
                            
                            logger.info(f"Successfully processed message from {from_number[-4:]}")
                            
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            # Send error message to user
                            error_msg = "Sorry, I encountered an error processing your message. Please try again."
                            await db.send_whatsapp_message(to=from_number, text=error_msg)

            return {"status": "success", "message": "Webhook processed"}
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def _setup_routes(self):
        """Setup webhook routes."""
        
        @self.router.get("/webhook", name="webhook_verify")
        async def verify_webhook(request: Request):
            """Verify webhook endpoint for WhatsApp API."""
            try:
                # Get query parameters directly from request
                params = dict(request.query_params)
                logger.info(f"Webhook verification request params: {params}")
                
                # Extract verification parameters
                mode = params.get("hub.mode")
                token = params.get("hub.verify_token")
                challenge = params.get("hub.challenge")
                
                logger.info(f"Verification attempt - Mode: {mode}, Token: {token}, Challenge: {challenge}")
                logger.info(f"Expected token: {self.verify_token}")
                
                # Verify token
                if mode == "subscribe" and token == self.verify_token:
                    if not challenge:
                        raise ValueError("Missing hub.challenge")
                    logger.info("Webhook verified successfully")
                    return Response(content=challenge, media_type="text/plain")
                
                logger.error(f"Token verification failed. Expected: {self.verify_token}, Got: {token}")
                raise ValueError("Invalid verification token")
                
            except ValueError as e:
                logger.error(f"Invalid challenge format: {e}")
                raise HTTPException(status_code=400, detail=str(e))
                
            except Exception as e:
                logger.error(f"Webhook verification failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.post("/webhook", name="webhook_handle")
        async def handle_webhook(request: Request) -> Dict[str, Any]:
            """Handle incoming webhook events."""
            return await self.handle_webhook_post(request)

    async def process_whatsapp_message(self, data: dict) -> bool:
        """Process incoming WhatsApp message webhook with validation."""
        try:
            # Validate basic webhook structure
            if not isinstance(data, dict) or "entry" not in data or not data["entry"]:
                logger.warning("Invalid webhook data structure")
                return False

            # Extract message data with validation
            try:
                entry = data["entry"][0]
                changes = entry["changes"][0]
                value = changes["value"]
            except (IndexError, KeyError) as e:
                logger.warning(f"Invalid webhook data structure: {str(e)}")
                return False

            # Validate message presence
            if "messages" not in value or not value["messages"]:
                logger.info("No messages in webhook data")
                return True

            # Extract and validate message
            try:
                message = value["messages"][0]
                from_number = message["from"]
                
                # Validate phone number format
                if not isinstance(from_number, str) or len(from_number) < 10:
                    logger.warning(f"Invalid phone number format: {from_number}")
                    return False
                
                # Log basic message info with masked phone
                logger.info(f"Processing message from {from_number[-4:]}")
                
                # Validate message type
                if not isinstance(message.get("type"), str):
                    logger.warning(f"Invalid message type from {from_number[-4:]}")
                    return False
                
                if message["type"] != "text":
                    logger.info(f"Ignoring non-text message type: {message['type']} from {from_number[-4:]}")
                    return True
                
                # Validate text message structure
                if not isinstance(message.get("text"), dict) or "body" not in message["text"]:
                    logger.warning(f"Invalid text message structure from {from_number[-4:]}")
                    return False
                
                # Extract and validate message text
                text = message["text"]["body"]
                if not isinstance(text, str) or len(text) > 1000:
                    logger.warning(f"Invalid message format from {from_number[-4:]}: length={len(text) if isinstance(text, str) else 'N/A'}")
                    return False
                
                # Validate text content
                text = text.strip()
                if not text:
                    logger.info(f"Empty message from {from_number[-4:]}")
                    return True
                
                # Log validated message content
                logger.info(f"Message content from {from_number[-4:]}: {text[:50]}{'...' if len(text) > 50 else ''}")
                
                # Process the validated message
                response = await process_incoming_message(from_number, text)
                
                # Validate response
                if not isinstance(response, str) or len(response) > 4096:  # WhatsApp message limit
                    logger.error(f"Invalid response format for {from_number[-4:]}")
                    response = "Sorry, I encountered an error. Please try again."
                
                # Log response with truncation
                logger.info(f"Sending response to {from_number[-4:]}: {response[:50]}{'...' if len(response) > 50 else ''}")
                
                # Send response via WhatsApp
                if not await db.send_whatsapp_message(from_number, response):
                    logger.error(f"Failed to send WhatsApp response to {from_number[-4:]}")
                    return False
                
                logger.info(f"Successfully processed message from {from_number[-4:]}")
                return True
                
            except KeyError as e:
                logger.warning(f"Missing required field in message structure: {str(e)}")
                return False
                
        except Exception as e:
            # Enhanced error logging with context
            logger.error(
                f"Error processing message from {from_number[-4:] if 'from_number' in locals() else 'unknown'}: {str(e)}",
                exc_info=True
            )
            return False

    async def process_webhook(self, data: dict) -> bool:
        """Process incoming webhook data."""
        try:
            # Validate webhook object type
            if data.get("object") != "whatsapp_business_account":
                logger.warning(f"Ignoring non-WhatsApp webhook: {data.get('object')}")
                return True
            
            # Process message if present
            if "entry" in data and data["entry"]:
                return await self.process_whatsapp_message(data)
            
            # Log other webhook types
            logger.info(f"Processed non-message webhook: {json.dumps(data, indent=2)}")
            return True
            
        except Exception as e:
            # Enhanced error logging for webhook processing
            logger.error(
                f"Error processing webhook data: {str(e)}",
                exc_info=True
            )
            logger.debug(f"Problematic webhook data: {json.dumps(data, indent=2)}")
            return False

# Create a single instance
webhook_service = WebhookService()
# Export the router
router = webhook_service.router 