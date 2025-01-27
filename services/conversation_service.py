"""
Service for managing conversations with database persistence.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from data.models import UserProfile, DietPlan, ConversationMessage
from data.database import db

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self):
        self.db = db

    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Récupère le profil utilisateur."""
        try:
            result = await self.db.get_user_profile(user_id)
            return UserProfile(**result) if result else None
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None

    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> bool:
        """Met à jour le profil utilisateur."""
        try:
            return await self.db.update_user_profile(user_id, profile_data)
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return False

    async def get_diet_plan(self, user_id: str) -> Optional[DietPlan]:
        """Récupère le plan alimentaire."""
        try:
            result = await self.db.get_diet_plan(user_id)
            return DietPlan(**result) if result else None
        except Exception as e:
            logger.error(f"Error getting diet plan: {str(e)}")
            return None

    async def update_diet_plan(self, user_id: str, plan_data: Dict[str, Any]) -> bool:
        """Met à jour le plan alimentaire."""
        try:
            return await self.db.update_diet_plan(user_id, plan_data)
        except Exception as e:
            logger.error(f"Error updating diet plan: {str(e)}")
            return False

    async def add_message(self, user_id: str, role: str, content: str) -> bool:
        """Ajoute un message à l'historique."""
        try:
            message = ConversationMessage(
                user_id=user_id,
                role=role,
                content=content
            )
            return await self.db.add_conversation_message(message)
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            return False

    async def get_recent_messages(self, user_id: str, limit: int = 10) -> List[ConversationMessage]:
        """Récupère les messages récents."""
        try:
            results = await self.db.get_conversation_history(user_id, limit)
            return [ConversationMessage(**msg) for msg in results]
        except Exception as e:
            logger.error(f"Error getting recent messages: {str(e)}")
            return []

# Instance globale du service
conversation_service = ConversationService() 