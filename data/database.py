"""
Database connection and operations module.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from .models import ConversationMessage, DietPlan, UserProfile, UserGoals

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """Initialize database connection."""
        try:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if not url or not key:
                raise ValueError("Missing Supabase credentials")
            
            self.client: Client = create_client(url, key)
            logger.info("Database connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            raise

    def table(self, name: str):
        """Get a table reference."""
        return self.client.table(name)

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile data."""
        try:
            result = self.table("users").select("*").eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None

    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Update user profile data."""
        try:
            profile_data["updated_at"] = datetime.utcnow().isoformat()
            result = self.table("users").upsert({
                "user_id": user_id,
                **profile_data
            }).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return False

    async def get_diet_plan(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user diet plan."""
        try:
            result = self.table("diet_plans").select("*").eq("user_id", user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting diet plan: {str(e)}")
            return None

    async def update_diet_plan(self, user_id: str, plan_data: Dict[str, Any]) -> bool:
        """Update user diet plan."""
        try:
            result = self.table("diet_plans").upsert({
                "user_id": user_id,
                **plan_data
            }).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error updating diet plan: {str(e)}")
            return False

    async def add_conversation_message(self, message: ConversationMessage) -> bool:
        """Add a message to conversation history."""
        try:
            result = self.table("conversations").insert(message.dict()).execute()
            return bool(result.data)
        except Exception as e:
            logger.error(f"Error adding conversation message: {str(e)}")
            return False

    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history."""
        try:
            result = self.table("conversations") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            return list(reversed(result.data)) if result.data else []
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []

# Global database instance
db = Database()