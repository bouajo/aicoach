"""
Package data: regroupe l'accès à la base et les modèles.
"""

from .database import db
from .models import (
    ConversationState,
    ConversationMessage,
    UserProfile,
    DietPlan,
    UserGoals
)

__all__ = [
    'db',
    'ConversationState',
    'ConversationMessage',
    'UserProfile',
    'DietPlan',
    'UserGoals'
] 