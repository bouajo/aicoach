"""
Database interface for Supabase.
"""

import logging
from typing import Dict, Any, Optional, List
import os
from supabase import create_client, Client
from datetime import datetime
from .models import ConversationMessage, UserProfile, DietPlan
import uuid

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """Initialize the database connection."""
        # Use service role key for full access
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_SERVICE_KEY", "")  # Use service role key for full access
        )
        logger.info("Database connection initialized with service role")
        
    def _phone_to_uuid(self, phone: str) -> str:
        """Convert phone number to a consistent UUID."""
        return str(uuid.uuid5(uuid.NAMESPACE_OID, phone))
        
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user's profile data.
        
        Args:
            user_id: The user's phone number
            
        Returns:
            Optional[Dict[str, Any]]: The user's profile data or None if not found
        """
        try:
            uuid_id = self._phone_to_uuid(user_id)
            response = self.supabase.table("user_profiles").select("*").eq("user_id", uuid_id).execute()
            if response.data and len(response.data) > 0:
                data = response.data[0]
                data["phone_number"] = user_id  # Add original phone number
                return data
            return None
            
        except Exception as e:
            logger.error(f"Error get_user_profile: {e}")
            return None
            
    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """
        Update or create a user's profile.
        
        Args:
            user_id: The user's phone number
            profile_data: The profile data to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert phone to UUID
            uuid_id = self._phone_to_uuid(user_id)
            
            # Ensure user_id is set to UUID
            profile_data["user_id"] = uuid_id
            profile_data["phone_number"] = user_id  # Store original phone number
            
            # Add timestamps
            now = datetime.now().isoformat()
            if "created_at" not in profile_data:
                profile_data["created_at"] = now
            profile_data["updated_at"] = now
            
            # Upsert the profile
            response = self.supabase.table("user_profiles").upsert(profile_data).execute()
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error update_user_profile: {e}")
            return False
            
    async def get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user's conversation context.
        
        Args:
            user_id: The user's phone number
            
        Returns:
            Optional[Dict[str, Any]]: The user's context data or None if not found
        """
        try:
            uuid_id = self._phone_to_uuid(user_id)
            response = self.supabase.table("conversation_summaries").select("*").eq("user_id", uuid_id).order("created_at", desc=True).limit(1).execute()
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error get_user_context: {e}")
            return None
            
    async def update_user_context(self, user_id: str, context_data: Dict[str, Any]) -> bool:
        """
        Update a user's conversation context.
        
        Args:
            user_id: The user's phone number
            context_data: The context data to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert phone to UUID
            uuid_id = self._phone_to_uuid(user_id)
            
            # Ensure user_id is set
            context_data["user_id"] = uuid_id
            
            # Add timestamps
            now = datetime.now().isoformat()
            if "created_at" not in context_data:
                context_data["created_at"] = now
            context_data["updated_at"] = now
            
            # Insert new context
            response = self.supabase.table("conversation_summaries").insert(context_data).execute()
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error update_user_context: {e}")
            return False
            
    async def add_message(self, user_id: str, role: str, content: str) -> bool:
        """
        Add a message to the conversation history.
        
        Args:
            user_id: The user's phone number
            role: The message role (user/assistant)
            content: The message content
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            uuid_id = self._phone_to_uuid(user_id)
            message_data = {
                "user_id": uuid_id,
                "role": role,
                "content": content,
                "created_at": datetime.now().isoformat()
            }
            
            response = self.supabase.table("conversation_messages").insert(message_data).execute()
            return bool(response.data)
            
        except Exception as e:
            logger.error(f"Error add_message: {e}")
            return False
            
    async def get_recent_messages(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent messages for a user.
        
        Args:
            user_id: The user's phone number
            limit: Maximum number of messages to return
            
        Returns:
            List[Dict[str, Any]]: List of recent messages
        """
        try:
            uuid_id = self._phone_to_uuid(user_id)
            response = self.supabase.table("conversation_messages").select("*").eq("user_id", uuid_id).order("created_at", desc=True).limit(limit).execute()
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error get_recent_messages: {e}")
            return []

    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            uuid_id = self._phone_to_uuid(user_id)
            result = (
                self.supabase.table("conversation_messages")
                .select("*")
                .eq("user_id", uuid_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return list(reversed(result.data)) if result.data else []
        except Exception as e:
            logger.error(f"Error get_conversation_history: {e}")
            return []

    async def get_diet_plan(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.supabase.table("diet_plans").select("*").eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error get_diet_plan: {e}")
            return None

    async def update_diet_plan(self, user_id: str, plan_data: Dict[str, Any]) -> bool:
        try:
            plan_data["updated_at"] = datetime.now().isoformat()
            result = self.supabase.table("diet_plans").upsert({"user_id": user_id, **plan_data}).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error update_diet_plan: {e}")
            return False

    async def delete_conversation_history(self, user_id: str) -> bool:
        try:
            result = self.supabase.table("conversation_messages").delete().eq("user_id", user_id).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error delete_conversation_history: {e}")
            return False

    async def get_messages_by_state(
        self, user_id: str, state: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        try:
            result = (
                self.supabase.table("conversation_messages")
                .select("*")
                .eq("user_id", user_id)
                .eq("conversation_state", state)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return list(reversed(result.data)) if result.data else []
        except Exception as e:
            logger.error(f"Error get_messages_by_state: {e}")
            return []

# Create a single instance
db = Database()