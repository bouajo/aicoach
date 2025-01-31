"""
Modèles de données (Pydantic) et enum pour la conversation.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from pydantic import BaseModel, Field

class ConversationState(str, Enum):
    INTRODUCTION = "introduction"
    LANGUAGE_SELECTION = "language_selection"
    LANGUAGE_CONFIRMATION = "language_confirmation"
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
            ConversationState.INTRODUCTION: ConversationState.LANGUAGE_SELECTION,
            ConversationState.LANGUAGE_SELECTION: ConversationState.LANGUAGE_CONFIRMATION,
            ConversationState.LANGUAGE_CONFIRMATION: ConversationState.NAME_COLLECTION,
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

class UserProfile(BaseModel):
    """User profile data model."""
    user_id: str
    conversation_state: str = "introduction"
    language: str = "français"
    first_name: Optional[str] = None
    age: Optional[int] = None
    height_cm: Optional[int] = None
    start_weight: Optional[float] = None
    current_weight: Optional[float] = None
    target_weight: Optional[float] = None
    target_date: Optional[date] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def is_complete(self) -> bool:
        """Vérifie si toutes les informations requises sont présentes."""
        return all([
            self.first_name,
            self.age,
            self.height_cm,
            self.start_weight,
            self.target_weight,
            self.target_date
        ])

    def next_required_field(self) -> Optional[str]:
        """Retourne le prochain champ requis."""
        required_fields = [
            "first_name",
            "age",
            "height_cm",
            "start_weight",
            "target_weight",
            "target_date"
        ]
        for field in required_fields:
            if not getattr(self, field):
                return field
        return None

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

class ConversationMessage(BaseModel):
    """Conversation message data model."""
    user_id: str
    role: str  # "user" ou "assistant"
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Surcharge pour formater les dates en ISO."""
        d = super().dict(*args, **kwargs)
        if "created_at" in d:
            d["created_at"] = d["created_at"].isoformat()
        return d