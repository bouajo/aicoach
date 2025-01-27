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
    user_id: str
    age: Optional[int] = None
    height_cm: Optional[int] = None
    current_weight: Optional[float] = None
    target_weight: Optional[float] = None
    target_date: Optional[int] = None  # Nombre de mois pour atteindre l'objectif
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    allergies: List[str] = Field(default_factory=list)
    preferences: List[str] = Field(default_factory=list)
    schedule_constraints: List[str] = Field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Vérifie si toutes les informations requises sont présentes."""
        return all([
            self.age,
            self.height_cm,
            self.current_weight,
            self.target_weight,
            self.target_date
        ])

    @property
    def next_required_field(self) -> Optional[str]:
        """Retourne le prochain champ requis."""
        fields = ["age", "height_cm", "current_weight", "target_weight", "target_date"]
        for field in fields:
            if not getattr(self, field):
                return field
        return None

class UserGoals(BaseModel):
    weight_loss: Optional[float] = None
    weekly_target: Optional[float] = None
    diet_preferences: List[str] = Field(default_factory=list)
    exercise_preferences: List[str] = Field(default_factory=list)

class DietPlan(BaseModel):
    user_id: str
    calories_per_day: int
    meals_per_day: int = 3
    created_at: datetime = Field(default_factory=datetime.utcnow)
    fasting_hours: Optional[int] = None
    restrictions: List[str] = Field(default_factory=list)
    supplements: List[str] = Field(default_factory=list)
    weekly_goals: List[str] = Field(default_factory=list)

class ConversationMessage(BaseModel):
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