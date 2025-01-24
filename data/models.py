"""
Data models for the application.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

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
            ConversationState.FOLLOW_UP: ConversationState.ACTIVE_COACHING
        }
        return states_flow.get(self, self)

class UserProfile(BaseModel):
    first_name: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[int] = None
    current_weight: Optional[float] = None
    target_weight: Optional[float] = None
    target_date: Optional[datetime] = None
    allergies: List[str] = Field(default_factory=list)
    preferences: List[str] = Field(default_factory=list)
    schedule_constraints: List[str] = Field(default_factory=list)

class UserGoals(BaseModel):
    weight_loss: Optional[float] = None
    weekly_target: Optional[float] = None
    diet_preferences: List[str] = Field(default_factory=list)
    exercise_preferences: List[str] = Field(default_factory=list)

class DietPlan(BaseModel):
    calories_per_day: int
    meals_per_day: int
    fasting_hours: Optional[int] = None
    restrictions: List[str] = Field(default_factory=list)
    supplements: List[str] = Field(default_factory=list)
    weekly_goals: List[str] = Field(default_factory=list)

class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class UserContext(BaseModel):
    user_id: str
    state: ConversationState = ConversationState.INTRODUCTION
    language: str = "français"
    profile: UserProfile = Field(default_factory=UserProfile)
    goals: UserGoals = Field(default_factory=UserGoals)
    diet_plan: Optional[DietPlan] = None
    conversation_history: List[ConversationMessage] = Field(default_factory=list)
    last_interaction: Optional[datetime] = None

    @classmethod
    def default(cls, user_id: str) -> 'UserContext':
        return cls(user_id=user_id)