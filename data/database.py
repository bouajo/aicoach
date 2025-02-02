"""
Database interface for Supabase.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest import APIError

# Load environment variables from all possible locations
env_paths = [
    Path.cwd() / '.env',  # Current directory
    Path.cwd().parent / '.env',  # Parent directory
    Path(__file__).parent.parent / '.env',  # Project root
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

logger = logging.getLogger(__name__)

class Database:
    """Database interface using Supabase."""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")
            
        self.client: Client = create_client(self.url, self.key)
        # Define known columns for each table
        self.user_profile_columns = [
            "user_id",
            "phone_number",
            "first_name",
            "language",
            "language_name",
            "is_rtl",
            "conversation_state",
            "age",
            "height_cm",
            "current_weight",
            "target_weight",
            "activity_level",
            "diet_restrictions",
            "health_conditions",
            "fields_to_ask",
            "created_at",
            "updated_at"
        ]
        
    def _filter_valid_columns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out data keys that don't exist as columns in the table."""
        return {k: v for k, v in data.items() if k in self.user_profile_columns}
        
    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by ID."""
        try:
            response = self.client.table("user_profiles").select("*").eq("user_id", user_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting user profile: {e}", exc_info=True)
            return None
            
    def update_user_profile(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Update or create a user profile.
        
        Args:
            user_id: The user's UUID
            data: The data to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Filter out invalid columns
            valid_data = self._filter_valid_columns(data)
            
            # Add user_id and timestamps
            valid_data["user_id"] = user_id
            valid_data["updated_at"] = datetime.utcnow().isoformat()
            if "created_at" not in valid_data:
                valid_data["created_at"] = valid_data["updated_at"]
            
            # Execute the update
            self.client.table("user_profiles").upsert(valid_data).execute()
            return True
            
        except APIError as e:
            logger.error(f"Error update_user_profile: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Error update_user_profile: {e}")
            return False
            
    def store_message(
        self,
        user_id: str,
        role: str,
        content: str
    ) -> bool:
        """Store a message in the conversation history."""
        try:
            data = {
                "user_id": user_id,
                "role": role,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }
            
            self.client.table("conversation_messages").insert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Error storing message: {e}", exc_info=True)
            return False
            
    def get_message_count(self, user_id: str) -> int:
        """Get the count of messages for a user."""
        try:
            response = self.client.table("conversation_messages").select("id").eq("user_id", user_id).execute()
            return len(response.data)
        except Exception as e:
            logger.error(f"Error getting message count: {e}", exc_info=True)
            return 0
            
    def get_recent_messages(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages for a user."""
        try:
            response = self.client.table("conversation_messages") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
                
            return response.data
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}", exc_info=True)
            return []
            
    def update_user_context(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Update user context."""
        try:
            # Ensure timestamps are in ISO format
            data["updated_at"] = datetime.utcnow().isoformat()
            if "created_at" not in data:
                data["created_at"] = data["updated_at"]
            
            # Ensure user_id is set
            data["user_id"] = user_id
            
            self.client.table("conversation_summaries").upsert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Error update_user_context: {e}", exc_info=True)
            return False
            
    def close(self):
        """Close database connection."""
        pass  # Supabase client doesn't require explicit closing

# Create a single instance
db = Database()