"""
Service for handling chat interactions across different platforms.
"""

import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from data.models import UserProfile, DietPlan, ConversationMessage
from managers import prompt_manager
from services.conversation_service import conversation_service
from services.ai_service import ai_service, AIProvider

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.data_collection_order = ["age", "height_cm", "current_weight", "target_weight", "target_date"]

    async def process_message(
        self,
        user_id: str,
        message: str,
        user_data: Optional[Dict[str, Any]] = None,
        provider: Optional[AIProvider] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Traite un message utilisateur et génère une réponse.
        Point d'entrée unifié pour toutes les plateformes.
        """
        try:
            # Récupération ou création du profil utilisateur
            profile = await self._get_or_create_profile(user_id, user_data)
            recent_messages = await conversation_service.get_recent_messages(user_id)
            is_new_user = len(recent_messages) == 0

            # Enregistrement du message utilisateur
            if not is_new_user:
                await conversation_service.add_message(user_id, "user", message)

            # Génération de la réponse
            if is_new_user:
                response = prompt_manager.get_initial_greeting()
            else:
                response = await self._process_user_response(user_id, profile, message, provider)

            # Enregistrement de la réponse
            await conversation_service.add_message(user_id, "assistant", response)

            # Mise à jour du profil si nécessaire
            if not is_new_user:
                await conversation_service.update_user_profile(user_id, profile.dict())

            return response, {
                "profile": profile.dict(),
                "is_complete": profile.is_complete
            }

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return "Une erreur s'est produite. Veuillez réessayer.", {}

    async def _process_user_response(
        self,
        user_id: str,
        profile: UserProfile,
        message: str,
        provider: Optional[AIProvider] = None
    ) -> str:
        """Traite la réponse de l'utilisateur et détermine la prochaine étape."""
        try:
            # Détermine quelle information nous collectons actuellement
            next_field = profile.next_required_field
            
            if not next_field:
                # Toutes les informations sont collectées, générer le résumé
                diet_plan = await conversation_service.get_diet_plan(user_id)
                prompt = prompt_manager.get_summary_prompt(profile, diet_plan)
            else:
                # Continuer la collecte de données
                prompt = prompt_manager.get_data_collection_prompt(
                    next_field,
                    profile,
                    message
                )

            # Obtient la réponse du modèle
            recent_messages = await conversation_service.get_recent_messages(user_id, limit=5)
            return await ai_service.get_response(
                prompt=prompt,
                conversation_history=[msg.dict() for msg in recent_messages],
                provider=provider
            )

        except Exception as e:
            logger.error(f"Error processing user response: {str(e)}")
            return "Désolé, j'ai rencontré un problème. Pouvez-vous reformuler ?"

    async def _get_or_create_profile(
        self,
        user_id: str,
        user_data: Optional[Dict[str, Any]] = None
    ) -> UserProfile:
        """Récupère ou crée le profil utilisateur."""
        try:
            # Essaie de récupérer le profil existant
            profile = await conversation_service.get_user_profile(user_id)
            if profile:
                return profile

            # Crée un nouveau profil
            profile_data = {"user_id": user_id}
            if user_data:
                profile_data.update(user_data)
            
            profile = UserProfile(**profile_data)
            await conversation_service.update_user_profile(user_id, profile.dict())
            return profile

        except Exception as e:
            logger.error(f"Error getting/creating user profile: {str(e)}")
            return UserProfile(user_id=user_id)

# Instance globale du service
chat_service = ChatService() 