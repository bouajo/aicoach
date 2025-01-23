"""
Data models for the application.
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel

class ConversationState(str, Enum):
    INTRODUCTION = "introduction"
    COLLECTING_DATA = "collecting_data"
    DIET_PLANNING = "diet_planning"
    ACTIVE_COACHING = "active_coaching"
    FOLLOW_UP = "follow_up"

    def next_state(self) -> 'ConversationState':
        """Returns the next state in the conversation flow."""
        states_flow = {
            ConversationState.INTRODUCTION: ConversationState.COLLECTING_DATA,
            ConversationState.COLLECTING_DATA: ConversationState.DIET_PLANNING,
            ConversationState.DIET_PLANNING: ConversationState.ACTIVE_COACHING,
            ConversationState.ACTIVE_COACHING: ConversationState.FOLLOW_UP,
            ConversationState.FOLLOW_UP: ConversationState.ACTIVE_COACHING  # Retour au coaching actif après le suivi
        }
        return states_flow.get(self, self)  # Si l'état n'est pas trouvé, retourne l'état actuel

class DietPlan(BaseModel):
    calories_per_day: int
    meals_per_day: int
    fasting_hours: Optional[int] = None
    restrictions: list[str] = []
    supplements: list[str] = []
    weekly_goals: list[str] = []

class UserData(BaseModel):
    conversation_state: str = ConversationState.INTRODUCTION
    language: str = "français"
    user_details: Dict[str, Any] = {}
    diet_plan: Optional[DietPlan] = None
    conversation_history: list[Dict[str, str]] = []