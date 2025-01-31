"""
Service for handling WhatsApp message reception/sending via Meta API.
"""

import os
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException, Query
from typing import Dict, Any
from dotenv import load_dotenv
from services.chat_service import chat_service

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
                await send_whatsapp_message(from_number, response)
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
                        await send_whatsapp_message(from_number, error_message)
                    except:
                        pass
                return {"status": "error", "detail": str(e)}

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {"status": "error", "detail": str(e)}

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return {"status": "error", "detail": str(e)}

async def send_whatsapp_message(to_number: str, message: str):
    """
    Send a message via WhatsApp API.
    """
    if not message or not message.strip():
        logger.error("Empty message content")
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    if not WHATSAPP_ACCESS_TOKEN:
        logger.error("WhatsApp access token is missing")
        raise HTTPException(status_code=500, detail="WhatsApp configuration error: Missing access token")
        
    if not PHONE_NUMBER_ID:
        logger.error("WhatsApp phone number ID is missing")
        raise HTTPException(status_code=500, detail="WhatsApp configuration error: Missing phone number ID")
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Ensure the message is properly formatted
    message = message.strip()
    if len(message) > 4096:  # WhatsApp message length limit
        message = message[:4093] + "..."
    
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {"preview_url": False, "body": message}
    }
    
    try:
        async with httpx.AsyncClient() as client:
            logger.debug(f"Sending WhatsApp message to {to_number}")
            logger.debug(f"Using API URL: {WHATSAPP_API_URL}")
            logger.debug(f"Headers: Authorization: Bearer <token>, Content-Type: {headers['Content-Type']}")
            logger.debug(f"Payload: {payload}")
            
            response = await client.post(
                WHATSAPP_API_URL, 
                headers=headers, 
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 401:
                error_data = response.json().get("error", {})
                error_msg = error_data.get("message", "Unknown authentication error")
                logger.error(f"WhatsApp authentication failed: {error_msg}")
                raise HTTPException(
                    status_code=500,
                    detail=f"WhatsApp authentication failed: {error_msg}"
                )
            
            if response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"WhatsApp API error (400): {error_msg}")
                logger.error(f"Full response: {error_data}")
                raise HTTPException(
                    status_code=400,
                    detail=f"WhatsApp API error: {error_msg}"
                )
                
            response.raise_for_status()
            response_data = response.json()
            logger.info(f"Message sent successfully to {to_number}")
            logger.debug(f"WhatsApp API response: {response_data}")
            return response_data
            
    except httpx.TimeoutException:
        logger.error(f"Timeout sending message to {to_number}")
        raise HTTPException(status_code=504, detail="WhatsApp API timeout")
        
    except httpx.HTTPStatusError as e:
        logger.error(f"Error sending message to {to_number}: {str(e)}")
        if e.response.status_code == 401:
            error_data = e.response.json().get("error", {})
            error_msg = error_data.get("message", "Unknown authentication error")
            logger.error(f"WhatsApp authentication failed: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"WhatsApp authentication failed: {error_msg}"
            )
        raise HTTPException(
            status_code=502, 
            detail=f"WhatsApp API error: {str(e)}"
        ) 