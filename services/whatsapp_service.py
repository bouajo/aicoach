"""
Service for handling WhatsApp message reception/sending via Meta API.
"""

import os
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from services.chat_service import chat_service
from datetime import datetime, timedelta

load_dotenv()
logger = logging.getLogger(__name__)
router = APIRouter()

# Load and validate environment variables
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

if not all([VERIFY_TOKEN, PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN]):
    logger.error("Missing required WhatsApp credentials in environment variables")
    raise ValueError(
        "Missing WhatsApp credentials. Please set WHATSAPP_VERIFY_TOKEN, "
        "WHATSAPP_PHONE_NUMBER_ID, and WHATSAPP_ACCESS_TOKEN in .env file"
    )

logger.info("WhatsApp credentials loaded successfully:")
logger.info(f"- Phone Number ID: {PHONE_NUMBER_ID}")
logger.info(f"- Verify Token: {VERIFY_TOKEN}")
logger.info(f"- Access Token length: {len(WHATSAPP_ACCESS_TOKEN)}")

WHATSAPP_API_URL = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"

class WhatsAppService:
    """Service for sending WhatsApp messages."""
    
    def __init__(self):
        self.phone_number_id = PHONE_NUMBER_ID
        self.access_token = WHATSAPP_ACCESS_TOKEN
        self.base_url = "https://graph.facebook.com/v17.0"
        self.token_expiry = None
        
        if not self.phone_number_id or not self.access_token:
            raise ValueError("WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN are required")
            
        self.client = None
        self._init_client()
        
    def _init_client(self) -> None:
        """Initialize or reinitialize the HTTP client."""
        if self.client:
            self.client.aclose()
            
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        
    def refresh_token(self, new_token: str) -> None:
        """
        Refresh the WhatsApp access token.
        
        Args:
            new_token: The new access token to use
        """
        self.access_token = new_token
        # Update token in environment and .env file
        os.environ["WHATSAPP_ACCESS_TOKEN"] = new_token
        self._update_env_file("WHATSAPP_ACCESS_TOKEN", new_token)
        # Reset token expiry
        self.token_expiry = datetime.utcnow() + timedelta(days=1)
        # Reinitialize client with new token
        self._init_client()
        logger.info("WhatsApp access token refreshed successfully")
        
    def _update_env_file(self, key: str, value: str) -> None:
        """Update a value in the .env file."""
        try:
            env_path = os.path.join(os.getcwd(), '.env')
            if not os.path.exists(env_path):
                return
                
            # Read current contents
            with open(env_path, 'r') as f:
                lines = f.readlines()
                
            # Update or add the key
            key_found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    key_found = True
                    break
                    
            if not key_found:
                lines.append(f"{key}={value}\n")
                
            # Write back to file
            with open(env_path, 'w') as f:
                f.writelines(lines)
                
        except Exception as e:
            logger.error(f"Error updating .env file: {e}")
            
    async def send_message(
        self,
        to: str,
        text: str,
        retry_on_auth_error: bool = True,
        max_retries: int = 3
    ) -> bool:
        """
        Send a WhatsApp message.
        
        Args:
            to: The recipient's phone number
            text: The message content
            retry_on_auth_error: Whether to retry on authentication failure
            max_retries: Maximum number of retries
            
        Returns:
            bool: Whether the message was sent successfully
            
        Raises:
            HTTPException: If the message could not be sent
        """
        if not self.client:
            self._init_client()
            
        retries = 0
        while retries < max_retries:
            try:
                # Prepare message data
                data = {
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to,
                    "type": "text",
                    "text": {"body": text}
                }
                
                # Send message
                response = await self.client.post(
                    f"/{self.phone_number_id}/messages",
                    json=data
                )
                
                # Handle response
                if response.status_code == 200:
                    return True
                    
                # Handle specific error cases
                if response.status_code == 401:
                    error_data = response.json()
                    error_message = error_data.get("error", {}).get("message", "Unknown authentication error")
                    logger.error(f"WhatsApp authentication failed: {error_message}")
                    
                    if retry_on_auth_error and "access token" in error_message.lower():
                        # Token expired, notify but continue
                        logger.warning("Access token expired, please refresh it")
                        retries += 1
                        continue
                        
                    raise HTTPException(
                        status_code=401,
                        detail=f"Token expired. Please refresh your WhatsApp access token."
                    )
                    
                # Handle other errors
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Error sending WhatsApp message: {response.text}"
                )
                
            except httpx.RequestError as e:
                logger.error(f"Error sending WhatsApp message: {e}")
                if retries < max_retries - 1:
                    retries += 1
                    continue
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to send WhatsApp message: {str(e)}"
                )
                
            except Exception as e:
                logger.error(f"Unexpected error sending message: {e}")
                if retries < max_retries - 1:
                    retries += 1
                    continue
                raise HTTPException(
                    status_code=500,
                    detail=f"Internal server error: {str(e)}"
                )
                
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message after {max_retries} retries"
        )
            
    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()

# Create a single instance
whatsapp = WhatsAppService()

@router.get("/")
@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verify webhook endpoint for WhatsApp API (GET request).
    Meta sends a GET request with these parameters to verify the webhook.
    """
    # Log all query parameters for debugging
    params = dict(request.query_params)
    logger.info("Received webhook verification request with params:")
    logger.info(f"Query parameters: {params}")
    
    # Get parameters
    hub_mode = params.get("hub.mode")
    hub_challenge = params.get("hub.challenge")
    hub_verify_token = params.get("hub.verify_token")
    
    logger.info("Parsed webhook parameters:")
    logger.info(f"- Mode: {hub_mode}")
    logger.info(f"- Challenge: {hub_challenge}")
    logger.info(f"- Verify Token: {hub_verify_token}")
    logger.info(f"- Expected Token: {VERIFY_TOKEN}")
    
    # Handle missing parameters
    if not all([hub_mode, hub_challenge, hub_verify_token]):
        logger.error("Missing required query parameters")
        return {"message": "Missing parameters"}
    
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        try:
            challenge = int(hub_challenge)
            logger.info(f"Returning challenge: {challenge}")
            return challenge
        except ValueError:
            logger.error(f"Invalid hub_challenge value: {hub_challenge}")
            raise HTTPException(status_code=400, detail="Invalid hub_challenge value")
    
    logger.error(f"Webhook verification failed - Invalid token: {hub_verify_token}")
    raise HTTPException(status_code=403, detail="Invalid verify token")

@router.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle incoming WhatsApp messages (POST request).
    Meta sends a POST request when a message is received.
    """
    try:
        data = await request.json()
        logger.debug(f"Received webhook data: {data}")

        # Ignore status updates and other non-message events
        if "messages" not in str(data):
            return {"status": "ignored", "reason": "not a message event"}

        # Extract message data
        entry = data.get("entry", [])
        if not entry:
            logger.warning("No entry in webhook data")
            return {"status": "no_entry"}

        changes = entry[0].get("changes", [])
        if not changes:
            logger.warning("No changes in webhook data")
            return {"status": "no_changes"}

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            logger.warning("No messages in webhook data")
            return {"status": "no_messages"}

        msg = messages[0]
        from_number = msg.get("from")
        text = msg.get("text", {})
        if not text:
            logger.warning("Message does not contain text")
            return {"status": "no_text"}
            
        text_body = text.get("body", "")
        if not from_number or not text_body:
            logger.warning(f"Invalid message format - from: {from_number}, text: {text_body}")
            return {"status": "invalid_message_format"}

        # Create unique user ID from phone number
        user_id = f"wa_{from_number}"
        logger.info(f"Processing message from user {user_id}: {text_body[:50]}...")

        try:
            # Process message through chat service
            response, _ = await chat_service.process_message(user_id, text_body)
            if not response or not response.strip():
                logger.error(f"Empty response generated for {user_id}")
                response = "Je suis désolé, mais je n'ai pas pu générer une réponse. Veuillez réessayer."

            logger.info(f"Generated response for {user_id}: {response[:50]}...")

            try:
                # Send response back via WhatsApp
                await whatsapp.send_message(from_number, response)
                logger.info(f"Response sent to {user_id}")
                return {"status": "success"}
            except HTTPException as e:
                if e.status_code == 500 and "access token" in str(e.detail).lower():
                    logger.error("WhatsApp authentication failed - please refresh your access token")
                    return {
                        "status": "error",
                        "detail": "WhatsApp authentication failed. Please refresh your access token.",
                        "error_type": "auth_error"
                    }
                # For other errors, try to send error message unless it's an auth error
                if "access token" not in str(e.detail).lower():
                    error_message = "Je suis désolé, mais j'ai rencontré une erreur. Veuillez réessayer dans un moment."
                    try:
                        await whatsapp.send_message(from_number, error_message)
                    except:
                        pass
                return {"status": "error", "detail": str(e)}

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {"status": "error", "detail": str(e)}

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {"status": "error", "detail": str(e)} 