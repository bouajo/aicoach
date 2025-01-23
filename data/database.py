"""
Database interactions using Supabase.
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
from data.models import UserData, DietPlan

load_dotenv()

class Database:
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("Missing Supabase credentials")
        
        self.client: Client = create_client(supabase_url, supabase_key)

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data from database."""
        try:
            response = self.client.table("users").select("*").eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error getting user {user_id}: {e}")
            return None

    def create_or_update_user(self, user_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create or update user data."""
        try:
            current_data = self.get_user(user_id)
            if current_data:
                # Update existing user
                merged_data = {**current_data, **data}
                response = self.client.table("users").update(merged_data).eq("user_id", user_id).execute()
            else:
                # Create new user
                data["user_id"] = user_id  # Use user_id instead of id
                response = self.client.table("users").insert(data).execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error updating user {user_id}: {e}")
            return None

    def add_conversation_entry(self, user_id: str, role: str, content: str) -> bool:
        """Add a conversation entry to the history."""
        try:
            entry = {
                "user_id": user_id,
                "role": role,
                "content": content
            }
            self.client.table("conversations").insert(entry).execute()
            return True
        except Exception as e:
            print(f"Error adding conversation entry: {e}")
            return False

    def save_diet_plan(self, user_id: str, plan: DietPlan) -> bool:
        """Save or update a diet plan."""
        try:
            data = {
                "user_id": user_id,
                "plan_data": plan.dict()
            }
            self.client.table("diet_plans").upsert(data).execute()
            return True
        except Exception as e:
            print(f"Error saving diet plan: {e}")
            return False

    def get_conversation_history(self, user_id: str, limit: int = 10) -> list:
        """Get recent conversation history."""
        try:
            response = self.client.table("conversations") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            return response.data
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []

# Create a singleton instance
db = Database()