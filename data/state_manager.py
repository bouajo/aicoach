"""
Manages conversation state transitions.
"""

from typing import Dict, Any
from .models import ConversationState

class StateManager:
    @staticmethod
    def get_next_state(current_state: str, user_data: Dict[str, Any], user_message: str = None) -> str:
        """Determine the next conversation state based on current state and data."""
        
        if current_state == "introduction":
            # Move to collecting data when we have first name and age
            if user_data.get("first_name") and user_data.get("age"):
                return "collecting_data"
                
        elif current_state == "collecting_data":
            # Move to validation when we have all required data
            required_fields = ["height", "current_weight", "target_weight", "target_date"]
            if all(user_data.get(field) for field in required_fields):
                return "validating_data"
                
        elif current_state == "validating_data":
            # Move to diet planning if user confirms
            if user_message and any(word in user_message.lower() for word in ["oui", "ok", "correct", "exact"]):
                return "diet_planning"
                
        elif current_state == "diet_planning":
            # Move to active coaching if user accepts the plan
            if user_message and any(word in user_message.lower() for word in ["oui", "ok", "d'accord", "parfait", "bien"]):
                return "active_coaching"
                
        return current_state 