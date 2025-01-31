"""
Gère les transitions d'état dans la conversation.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from data.models import ConversationState, UserProfile
from data.validators import validate_user_profile

logger = logging.getLogger(__name__)

class StateManager:
    """Gère les transitions d'état et la validation des données."""
    
    def determine_next_state(
        self,
        current_state: ConversationState,
        user_profile: UserProfile,
        message: str
    ) -> Tuple[ConversationState, Optional[str]]:
        """
        Détermine le prochain état en fonction de l'état actuel et des données utilisateur.
        
        Args:
            current_state: État actuel de la conversation
            user_profile: Profil de l'utilisateur
            message: Dernier message de l'utilisateur
            
        Returns:
            Tuple (prochain_état, message_erreur)
        """
        try:
            # Valider les données actuelles
            profile_data = user_profile.dict()
            try:
                validate_user_profile(profile_data)
            except ValueError as e:
                return current_state, str(e)
            
            # Si toutes les données sont collectées, passer à la génération du plan
            if user_profile.is_complete:
                if current_state == ConversationState.DIET_RESTRICTIONS:
                    return ConversationState.PLAN_GENERATION, None
                elif current_state == ConversationState.PLAN_GENERATION:
                    return ConversationState.PLAN_REVIEW, None
                elif current_state == ConversationState.PLAN_REVIEW:
                    return ConversationState.FREE_CHAT, None
            
            # Sinon, passer au prochain champ requis
            next_field = user_profile.next_required_field()
            if next_field:
                return self._get_state_for_field(next_field), None
                
            # Par défaut, rester dans l'état actuel
            return current_state, None
            
        except Exception as e:
            logger.error(f"Erreur dans la transition d'état: {str(e)}")
            return current_state, "Une erreur est survenue. Veuillez réessayer."

    def _get_state_for_field(self, field_name: str) -> ConversationState:
        """Retourne l'état correspondant au champ à collecter."""
        field_to_state = {
            "first_name": ConversationState.NAME_COLLECTION,
            "age": ConversationState.AGE_COLLECTION,
            "height_cm": ConversationState.HEIGHT_COLLECTION,
            "current_weight": ConversationState.START_WEIGHT_COLLECTION,
            "target_weight": ConversationState.GOAL_COLLECTION,
            "target_date": ConversationState.TARGET_DATE_COLLECTION
        }
        return field_to_state.get(field_name, ConversationState.INTRODUCTION)

    def validate_field_value(self, field_name: str, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Valide une valeur pour un champ donné.
        
        Args:
            field_name: Nom du champ à valider
            value: Valeur à valider
            
        Returns:
            Tuple (est_valide, message_erreur)
        """
        try:
            test_data = {"user_id": "test", field_name: value}
            validate_user_profile(test_data)
            return True, None
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f"Erreur de validation: {str(e)}")
            return False, "Une erreur est survenue lors de la validation."

# Instance globale
state_manager = StateManager()