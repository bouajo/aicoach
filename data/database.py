"""
Database interaction layer using Supabase.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from postgrest import APIError
from supabase import create_client, Client
from .models import UserContext, ConversationMessage

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Missing Supabase credentials")
        self.client: Client = create_client(url, key)

    def extract_user_data(self, text: str, current_state: str, user_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract relevant data from user message based on conversation state."""
        text = text.strip().lower()
        
        if current_state == "introduction":
            # Extract name or age
            if not any(char.isdigit() for char in text):
                return {"first_name": text.capitalize()}
            else:
                # Extract age (take first number found)
                age = ''.join(filter(str.isdigit, text))
                return {"age": int(age)} if age else {}
                
        elif current_state == "collecting_data":
            # Get current profile data
            user_data = user_data or {}
            
            # Extract height, weights, or date
            if "cm" in text or (not user_data.get('height') and text.isdigit() and 140 <= int(text) <= 220):
                number = ''.join(filter(str.isdigit, text))
                if number:
                    return {"height": int(number)}
                    
            elif any(month in text for month in ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]):
                try:
                    # Parse month and year
                    words = text.split()
                    month_map = {
                        "janvier": 1, "février": 2, "mars": 3, "avril": 4,
                        "mai": 5, "juin": 6, "juillet": 7, "août": 8,
                        "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12
                    }
                    
                    month = None
                    year = None
                    
                    for word in words:
                        if word in month_map:
                            month = month_map[word]
                        elif word.isdigit() and len(word) == 4:
                            year = int(word)
                            
                    if month and year:
                        from datetime import date
                        target_date = date(year, month, 1)
                        return {"target_date": target_date.isoformat()}
                except:
                    return {}
                    
            elif any(char.isdigit() for char in text):
                number = ''.join(filter(str.isdigit, text))
                if number:
                    weight = float(number)
                    # If we don't have current_weight yet, set it
                    if not user_data.get('current_weight') and 40 <= weight <= 300:
                        return {"current_weight": weight}
                    # If we have current_weight but no target_weight, set target
                    elif not user_data.get('target_weight') and weight < user_data.get('current_weight', 300):
                        return {"target_weight": weight}
        
        return {}

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data from database."""
        try:
            response = self.client.table("users").select("*").eq("user_id", user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None

    def create_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Create a new user record."""
        try:
            data = {
                "user_id": user_id,
                "first_name": None,
                "age": None,
                "height": None,
                "current_weight": None,
                "target_weight": None,
                "target_date": None,
                "language": "français",
                "conversation_state": "introduction"
            }
            response = self.client.table("users").insert(data).execute()
            if not response.data:
                logger.error("No data returned after user creation")
                return None
            return response.data[0]
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            return None

    def update_user(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Update user data."""
        try:
            # Ensure we're not trying to update user_id
            if 'user_id' in data:
                del data['user_id']
            
            # Add updated_at timestamp
            data['updated_at'] = datetime.utcnow().isoformat()
            
            # Convert None values to SQL NULL
            for key, value in data.items():
                if value is None:
                    data[key] = None
            
            response = self.client.table("users").update(data).eq("user_id", user_id).execute()
            return bool(response.data)
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}", exc_info=True)
            return False

    def add_conversation_entry(self, user_id: str, role: str, content: str) -> bool:
        """Add a conversation entry."""
        try:
            self.client.table("conversations").insert({
                "user_id": user_id,
                "role": role,
                "content": content
            }).execute()
            return True
        except Exception as e:
            logger.error(f"Error adding conversation entry: {str(e)}")
            return False

    def get_conversation_history(self, user_id: str, limit: int = 10) -> List[ConversationMessage]:
        """Get recent conversation history."""
        try:
            response = self.client.table("conversations") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .execute()
            
            return [
                ConversationMessage(role=msg["role"], content=msg["content"])
                for msg in reversed(response.data)
            ] if response.data else []
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []

# Global database instance
db = Database()