"""
Modèles de données (Pydantic) et enum pour la conversation.
"""

from enum import Enum
from typing import Dict, Any, Optional, List, TypedDict
from datetime import datetime, date
from pydantic import BaseModel, Field

class ConversationState(str, Enum):
    LANGUAGE_DETECTION = "language_detection"
    INTRODUCTION = "introduction"
    NAME_COLLECTION = "name_collection"
    AGE_COLLECTION = "age_collection"
    HEIGHT_COLLECTION = "height_collection"
    START_WEIGHT_COLLECTION = "start_weight_collection"
    GOAL_COLLECTION = "goal_collection"
    TARGET_DATE_COLLECTION = "target_date_collection"
    DIET_PREFERENCES = "diet_preferences"
    DIET_RESTRICTIONS = "diet_restrictions"
    PLAN_GENERATION = "plan_generation"
    PLAN_REVIEW = "plan_review"
    FREE_CHAT = "free_chat"

    def next_state(self) -> 'ConversationState':
        """Returns the next state in the conversation flow."""
        states_flow = {
            ConversationState.LANGUAGE_DETECTION: ConversationState.INTRODUCTION,
            ConversationState.INTRODUCTION: ConversationState.NAME_COLLECTION,
            ConversationState.NAME_COLLECTION: ConversationState.AGE_COLLECTION,
            ConversationState.AGE_COLLECTION: ConversationState.HEIGHT_COLLECTION,
            ConversationState.HEIGHT_COLLECTION: ConversationState.START_WEIGHT_COLLECTION,
            ConversationState.START_WEIGHT_COLLECTION: ConversationState.GOAL_COLLECTION,
            ConversationState.GOAL_COLLECTION: ConversationState.TARGET_DATE_COLLECTION,
            ConversationState.TARGET_DATE_COLLECTION: ConversationState.DIET_PREFERENCES,
            ConversationState.DIET_PREFERENCES: ConversationState.DIET_RESTRICTIONS,
            ConversationState.DIET_RESTRICTIONS: ConversationState.PLAN_GENERATION,
            ConversationState.PLAN_GENERATION: ConversationState.PLAN_REVIEW,
            ConversationState.PLAN_REVIEW: ConversationState.FREE_CHAT,
            ConversationState.FREE_CHAT: ConversationState.FREE_CHAT
        }
        return states_flow.get(self, self)

class ConversationMessage(TypedDict):
    id: str
    user_id: str
    role: str  # 'user' or 'assistant'
    content: str
    created_at: str

class ConversationSummary(TypedDict):
    user_id: str
    summary: str
    created_at: str
    updated_at: str
    last_message_id: str  # Reference to the last message included in this summary

class UserProfile(TypedDict):
    user_id: str
    first_name: Optional[str]
    age: Optional[int]
    height_cm: Optional[float]
    current_weight: Optional[float]
    target_weight: Optional[float]
    language: Optional[str]
    language_name: Optional[str]
    is_rtl: Optional[bool]
    created_at: str
    updated_at: str
    last_interaction: Optional[str]
    onboarding_completed: Optional[bool]

class UserGoals(BaseModel):
    weight_loss: Optional[float] = None
    weekly_target: Optional[float] = None
    diet_preferences: List[str] = Field(default_factory=list)
    exercise_preferences: List[str] = Field(default_factory=list)

class DietPlan(BaseModel):
    """Diet plan data model."""
    user_id: str
    daily_calories: Optional[int] = None
    protein_ratio: Optional[float] = None
    carbs_ratio: Optional[float] = None
    fat_ratio: Optional[float] = None
    meal_frequency: Optional[int] = None
    restrictions: List[str] = Field(default_factory=list)
    preferences: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserContext(TypedDict):
    user_id: str
    conversation_summary: str
    last_topics: list[str]
    last_interaction: str
    created_at: str
    updated_at: str