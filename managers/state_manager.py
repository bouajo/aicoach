"""
Manages conversation state transitions.
"""

from typing import Dict, Any, Optional
from data.models import ConversationState

class StateManager:
    def __init__(self):
        # Définition des transitions de base
        self.transitions = {
            ConversationState.INTRODUCTION: ConversationState.COLLECTING_DATA,
            ConversationState.COLLECTING_DATA: ConversationState.DIET_PLANNING,
            ConversationState.DIET_PLANNING: ConversationState.ACTIVE_COACHING,
            ConversationState.ACTIVE_COACHING: ConversationState.FOLLOW_UP,
            ConversationState.FOLLOW_UP: ConversationState.ACTIVE_COACHING
        }

    def get_next_state(self, current_state: ConversationState, user_data: Optional[Dict[str, Any]] = None, user_message: Optional[str] = None) -> ConversationState:
        """
        Determine the next conversation state based on current state, user data, and message.
        
        Args:
            current_state: Current conversation state
            user_data: Optional user data dictionary
            user_message: Optional user message text
            
        Returns:
            Next conversation state
        """
        if not user_data:
            user_data = {}
            
        # Vérification des conditions de transition basées sur les données
        if current_state == ConversationState.INTRODUCTION:
            if user_data.get("first_name") and user_data.get("age"):
                return ConversationState.COLLECTING_DATA
                
        elif current_state == ConversationState.COLLECTING_DATA:
            required_fields = ["height", "current_weight", "target_weight", "target_date"]
            if all(user_data.get(field) for field in required_fields):
                return ConversationState.DIET_PLANNING
                
        elif current_state == ConversationState.DIET_PLANNING:
            # Transition vers le coaching actif si l'utilisateur accepte le plan
            if user_message and any(word in user_message.lower() for word in ["oui", "ok", "d'accord", "parfait", "bien"]):
                return ConversationState.ACTIVE_COACHING
                
        elif current_state == ConversationState.ACTIVE_COACHING:
            # Transition vers le suivi basée sur des conditions spécifiques
            # (à implémenter selon vos besoins)
            pass
            
        # Si aucune condition spéciale n'est remplie, utiliser la transition par défaut
        return self.transitions.get(current_state, current_state)

    def validate_state_transition(self, from_state: ConversationState, to_state: ConversationState) -> bool:
        """
        Valide si une transition d'état est autorisée.
        
        Args:
            from_state: État de départ
            to_state: État d'arrivée
            
        Returns:
            True si la transition est valide
        """
        # Vérifie si la transition est dans la liste des transitions autorisées
        if from_state in self.transitions and self.transitions[from_state] == to_state:
            return True
            
        # Vérifie les cas spéciaux (comme le retour au coaching actif depuis le suivi)
        if from_state == ConversationState.FOLLOW_UP and to_state == ConversationState.ACTIVE_COACHING:
            return True
            
        return False

    def get_state_requirements(self, state: ConversationState) -> Dict[str, Any]:
        """
        Retourne les exigences de données pour un état donné.
        
        Args:
            state: État de la conversation
            
        Returns:
            Dictionnaire des champs requis et leurs types
        """
        requirements = {
            ConversationState.INTRODUCTION: {
                "first_name": str,
                "age": int
            },
            ConversationState.COLLECTING_DATA: {
                "height": int,
                "current_weight": float,
                "target_weight": float,
                "target_date": str
            },
            ConversationState.DIET_PLANNING: {
                "height": int,
                "current_weight": float,
                "target_weight": float,
                "target_date": str,
                "allergies": list,
                "preferences": list
            }
        }
        return requirements.get(state, {})

# Instance globale du service
state_manager = StateManager()