from fastapi import Request, Response, HTTPException, APIRouter
from typing import Dict, Any
import logging
import os
from agent import process_incoming_message
from database import db

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
                            
                            logger.info(f"Successfully processed message from {from_number}")
                            
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

# Create a single instance
webhook_service = WebhookService()
# Export the router
router = webhook_service.router 