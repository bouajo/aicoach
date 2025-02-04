"""
database.py - Fixed Version
"""

import os
import logging
import httpx
import uuid
import json
from supabase import create_client, Client
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_fixed
from datetime import datetime

load_dotenv()
logger = logging.getLogger(__name__)

# Environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # Using service key for full access
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

# Fix 1: Update error message to match actual checked variables
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials (SUPABASE_URL, SUPABASE_SERVICE_KEY).")

if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
    raise ValueError("Missing WhatsApp API credentials (WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID).")

class Database:
    def __init__(self):
        """Initialize database connection."""
        logger.debug("Initializing Database connection")
        try:
            # Fix 2: Simplify client initialization
            self.client: Client = create_client(
                supabase_url=SUPABASE_URL,
                supabase_key=SUPABASE_KEY
            )
            logger.info("Successfully initialized Supabase client")
            
            # WhatsApp API configuration
            self.whatsapp_base_url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_ID}/messages"
            self.whatsapp_headers = {
                "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                "Content-Type": "application/json"
            }
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {str(e)}")
            raise

    def phone_to_uuid(self, phone_number: str) -> str:
        """Convert phone number to deterministic UUID."""
        try:
            uid = str(uuid.uuid5(uuid.NAMESPACE_DNS, phone_number))
            logger.debug(f"Generated UUID for phone number {phone_number[-4:]}: {uid}")
            return uid
        except Exception as e:
            logger.error(f"Error generating UUID for phone {phone_number[-4:]}: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def get_user_profile(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Retrieve user profile from database with retry logic."""
        try:
            logger.debug(f"Attempting to retrieve profile for user: {phone_number[-4:]}")
            uid = self.phone_to_uuid(phone_number)
            
            logger.debug(f"Executing Supabase query for user_id: {uid}")
            resp = self.client.table("user_profiles").select("*").eq("user_id", uid).execute()
            
            if resp.data and len(resp.data) > 0:
                logger.info(f"Retrieved profile for user: {phone_number[-4:]}")
                logger.debug(f"Profile data: {json.dumps(resp.data[0], indent=2)}")
                return resp.data[0]
            
            logger.info(f"No profile found for user: {phone_number[-4:]}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving user profile: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def create_user_profile(self, phone_number: str) -> bool:
        """Create new user profile with retry logic."""
        try:
            logger.debug(f"Attempting to create profile for user: {phone_number[-4:]}")
            uid = self.phone_to_uuid(phone_number)
            
            data = {
                "user_id": uid,
                "phone_number": phone_number,
                "language": "und",
                "step": "new"
            }
            logger.debug(f"Insert data prepared: {json.dumps(data, indent=2)}")
            
            resp = self.client.table("user_profiles").insert(data).execute()
            logger.debug(f"Supabase insert response: {json.dumps(resp.data if resp.data else {}, indent=2)}")
            
            if resp.data:
                logger.info(f"Successfully created profile for user: {phone_number[-4:]}")
                return True
                
            logger.error(f"Failed to create profile for user: {phone_number[-4:]}")
            return False
            
        except Exception as e:
            logger.error(f"Error creating user profile: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def update_user_profile(self, phone_number: str, updates: Dict[str, Any]) -> bool:
        """Update existing user profile with retry logic."""
        try:
            logger.debug(f"Attempting to update profile for user: {phone_number[-4:]}")
            uid = self.phone_to_uuid(phone_number)
            
            # Convert 'now()' to actual timestamp
            updates["updated_at"] = datetime.utcnow().isoformat()
            
            logger.debug(f"Update data prepared: {json.dumps(updates, indent=2)}")
            logger.debug(f"Updating user_id: {uid}")
            
            resp = self.client.table("user_profiles") \
                .update(updates) \
                .eq("user_id", uid) \
                .execute()
                
            logger.debug(f"Supabase update response: {json.dumps(resp.data if resp.data else {}, indent=2)}")
                
            if resp.data:
                logger.info(f"Successfully updated profile for user: {phone_number[-4:]} | Updates: {json.dumps(updates, indent=2)}")
                return True
                
            logger.error(f"Failed to update profile for user: {phone_number[-4:]}")
            logger.error("Empty response from Supabase update")
            return False
            
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def log_message(self, phone_number: str, role: str, content: str) -> bool:
        """Log message to database with retry logic."""
        try:
            logger.debug(f"Attempting to log message for user: {phone_number[-4:]}")
            logger.debug(f"Message details - Role: {role}, Content length: {len(content)}")
            
            data = {
                "phone_number": phone_number,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            logger.debug(f"Message data prepared: {json.dumps(data, indent=2)}")
            
            resp = self.client.table("conversation_messages").insert(data).execute()
            logger.debug(f"Supabase message log response: {json.dumps(resp.data if resp.data else {}, indent=2)}")
            
            if resp.data:
                logger.info(f"Successfully logged message for user: {phone_number[-4:]}")
                return True
                
            logger.error(f"Failed to log message for user: {phone_number[-4:]}")
            return False
            
        except Exception as e:
            logger.error(f"Error logging message: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return False

    def get_last_assistant_message(self, phone_number: str) -> Optional[str]:
        """Get the last assistant message for a user."""
        try:
            logger.debug(f"Retrieving last assistant message for user: {phone_number[-4:]}")
            
            resp = self.client.table("conversation_messages") \
                .select("content") \
                .eq("phone_number", phone_number) \
                .eq("role", "assistant") \
                .order("timestamp", desc=True) \
                .limit(1) \
                .execute()
                
            logger.debug(f"Supabase query response: {json.dumps(resp.data if resp.data else [], indent=2)}")
            
            if resp.data and len(resp.data) > 0:
                message = resp.data[0]["content"]
                logger.info(f"Retrieved last assistant message for user: {phone_number[-4:]}")
                logger.debug(f"Message content: {message}")
                return message
                
            logger.info(f"No assistant messages found for user: {phone_number[-4:]}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving last assistant message: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return None

    async def send_whatsapp_message(self, to: str, text: str) -> bool:
        """Send WhatsApp message using Meta's API (remains async for HTTP calls)."""
        try:
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": text}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.whatsapp_base_url,
                    headers=self.whatsapp_headers,
                    json=data
                )
                
                if response.status_code == 200:
                    logger.info(f"Sent WhatsApp message to: {to[-4:]}")
                    return True
                    
                logger.error(f"Failed to send WhatsApp message: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False

# Create a singleton instance
db = Database()
