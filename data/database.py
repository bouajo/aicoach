"""
Module de connexion à la base Supabase et opérations de base.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from .models import ConversationMessage, UserProfile, DietPlan

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Missing Supabase credentials (SUPABASE_URL / SUPABASE_KEY)")
        self.client: Client = create_client(url, key)
        logger.info("Supabase connection initialized.")

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.client.table("users").select("*").eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error get_user_profile: {e}")
            return None

    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        try:
            profile_data["updated_at"] = datetime.utcnow().isoformat()
            result = self.client.table("users").upsert({"user_id": user_id, **profile_data}).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error update_user_profile: {e}")
            return False

    async def get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = self.client.table("user_context").select("*").eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error get_user_context: {e}")
            return None

    async def update_user_context(self, user_id: str, context_data: Dict[str, Any]) -> bool:
        try:
            context_data["last_updated"] = datetime.utcnow().isoformat()
            result = self.client.table("user_context").upsert({"user_id": user_id, **context_data}).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error update_user_context: {e}")
            return False

    async def add_conversation_message(self, message: ConversationMessage) -> bool:
        try:
            data = message.dict()
            data["created_at"] = datetime.utcnow().isoformat()
            result = self.client.table("conversations").insert(data).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error add_conversation_message: {e}")
            return False

    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            result = (
                self.client.table("conversations")
                .select("*")
                .eq("user_id", user_id)
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
            result = self.client.table("diet_plans").select("*").eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error get_diet_plan: {e}")
            return None

    async def update_diet_plan(self, user_id: str, plan_data: Dict[str, Any]) -> bool:
        try:
            plan_data["updated_at"] = datetime.utcnow().isoformat()
            result = self.client.table("diet_plans").upsert({"user_id": user_id, **plan_data}).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error update_diet_plan: {e}")
            return False

    async def delete_conversation_history(self, user_id: str) -> bool:
        try:
            result = self.client.table("conversations").delete().eq("user_id", user_id).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error delete_conversation_history: {e}")
            return False

    async def get_messages_by_state(
        self, user_id: str, state: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        try:
            result = (
                self.client.table("conversations")
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

# Global database instance
db = Database()