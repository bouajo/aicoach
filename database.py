"""
database.py
A simple interface for Supabase + WhatsApp sending logic.
"""

import os
import logging
import httpx
import uuid
import json
from supabase import create_client, Client
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment.")

if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
    raise ValueError("Missing WhatsApp API credentials (WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID).")

class Database:
    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.whatsapp_base_url = f"https://graph.facebook.com/v17.0/{WHATSAPP_PHONE_ID}/messages"
        self.whatsapp_headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }

    def phone_to_uuid(self, phone_number: str) -> str:
        """Convert phone number to deterministic UUID."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, phone_number))

    def get_user_profile(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Retrieve the user profile by phone_number."""
        try:
            uid = self.phone_to_uuid(phone_number)
            resp = self.client.table("user_profiles").select("*").eq("user_id", uid).execute()
            if resp.data:
                logger.info(f"Retrieved profile for user: {phone_number[-4:]}")
                return resp.data[0]
            logger.info(f"No profile found for user: {phone_number[-4:]}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving user profile: {e}")
            return None

    def create_user_profile(self, phone_number: str) -> bool:
        """Create a user profile for a new user."""
        try:
            uid = self.phone_to_uuid(phone_number)
            data = {
                "user_id": uid,
                "phone_number": phone_number,
                "language": "und",  # undefined
                "step": "new"
            }
            resp = self.client.table("user_profiles").insert(data).execute()
            if resp.data:
                logger.info(f"Created profile for user: {phone_number[-4:]}")
                return True
            logger.error(f"Failed to create profile for user: {phone_number[-4:]}")
            return False
        except Exception as e:
            logger.error(f"Error creating user profile: {e}")
            return False

    def update_user_profile(self, phone_number: str, updates: Dict[str, Any]) -> bool:
        """Update user profile fields."""
        try:
            uid = self.phone_to_uuid(phone_number)
            updates["updated_at"] = "now()"
            resp = self.client.table("user_profiles").update(updates).eq("user_id", uid).execute()
            if resp.data:
                logger.info(f"Updated profile for user: {phone_number[-4:]} | Updates: {json.dumps(updates, indent=2)}")
                return True
            logger.error(f"Failed to update profile for user: {phone_number[-4:]}")
            return False
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            return False

    def log_message(self, phone_number: str, role: str, content: str) -> bool:
        """Store conversation message."""
        try:
            uid = self.phone_to_uuid(phone_number)
            data = {
                "user_id": uid,
                "role": role,
                "content": content
            }
            resp = self.client.table("conversation_messages").insert(data).execute()
            if resp.data:
                logger.info(f"Logged message for user: {phone_number[-4:]} | Role: {role}")
                return True
            logger.error(f"Failed to log message for user: {phone_number[-4:]}")
            return False
        except Exception as e:
            logger.error(f"Error logging message: {e}")
            return False

    async def send_whatsapp_message(self, to: str, text: str) -> bool:
        """Call the Meta WhatsApp Cloud API to send text back to the user."""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "text": {
                    "body": text
                }
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.whatsapp_base_url,
                    headers=self.whatsapp_headers,
                    json=payload
                )
                resp.raise_for_status()
                logger.info(f"Sent WhatsApp message to: {to[-4:]}")
                return True
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            return False

    async def get_last_assistant_message(self, phone_number: str) -> Optional[str]:
        """Retrieve the last message sent by the assistant to the user.
        
        Args:
            phone_number: The user's phone number
            
        Returns:
            The last message text or None if not found
        """
        try:
            response = self.client.table("conversation_messages").select("content") \
                .eq("phone_number", phone_number) \
                .eq("role", "assistant") \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()
                
            if response.data and len(response.data) > 0:
                return response.data[0]["content"]
            return None
            
        except Exception as e:
            logger.error(f"Error getting last assistant message: {e}")
            return None

# Create a singleton
db = Database()
