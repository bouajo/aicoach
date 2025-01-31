"""
Gère la séquence de collecte de données et l'avancement dans les étapes.
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from data.models import ConversationState, UserProfile

logger = logging.getLogger(__name__)

class FlowManager:
    """Gère le flux de conversation et la collecte de données."""
    
    def __init__(self):
        self.data_collection_order = [
            "language",
            "first_name",
            "age",
            "height_cm",
            "current_weight",
            "target_weight",
            "target_date",
            "diet_preferences",
            "diet_restrictions"
        ]

    def get_next_required_field(self, profile: UserProfile) -> Optional[str]:
        """Détermine le prochain champ à collecter."""
        profile_dict = profile.dict()
        for field in self.data_collection_order:
            if not profile_dict.get(field):
                return field
        return None

    def determine_next_state(
        self,
        current_state: ConversationState,
        user_profile: UserProfile,
        message: str
    ) -> Tuple[ConversationState, Optional[str]]:
        """
        Détermine le prochain état de la conversation.
        
        Args:
            current_state: État actuel
            user_profile: Profil utilisateur
            message: Message de l'utilisateur
            
        Returns:
            Tuple (prochain_état, message_erreur)
        """
        try:
            # Gestion de l'introduction
            if current_state == ConversationState.INTRODUCTION:
                return ConversationState.LANGUAGE_SELECTION, None
                
            # Language selection
            if current_state == ConversationState.LANGUAGE_SELECTION:
                value = message.strip().upper()
                if any(french in value for french in ["FR", "FRANÇAIS", "FRENCH", "FRANCAIS"]):
                    return ConversationState.LANGUAGE_CONFIRMATION, None
                elif any(english in value for english in ["EN", "ENGLISH", "ANGLAIS"]):
                    return ConversationState.LANGUAGE_CONFIRMATION, None
                return current_state, "Please specify your language preference (English or Français)"
                
            # Collecte du nom
            if current_state == ConversationState.NAME_COLLECTION:
                if not message.strip():
                    return current_state, "Veuillez indiquer votre prénom"
                return ConversationState.AGE_COLLECTION, None
                
            # Collecte de l'âge
            if current_state == ConversationState.AGE_COLLECTION:
                try:
                    age = int(message.strip())
                    if age < 12 or age > 100:
                        return current_state, "L'âge doit être entre 12 et 100 ans"
                    return ConversationState.HEIGHT_COLLECTION, None
                except ValueError:
                    return current_state, "Veuillez entrer un nombre valide pour votre âge"
                    
            # Collecte de la taille
            if current_state == ConversationState.HEIGHT_COLLECTION:
                try:
                    height = int(message.strip())
                    if height < 100 or height > 250:
                        return current_state, "La taille doit être entre 100 et 250 cm"
                    return ConversationState.START_WEIGHT_COLLECTION, None
                except ValueError:
                    return current_state, "Veuillez entrer un nombre valide pour votre taille en cm"
                    
            # Collecte du poids actuel
            if current_state == ConversationState.START_WEIGHT_COLLECTION:
                try:
                    weight = float(message.strip())
                    if weight < 30 or weight > 300:
                        return current_state, "Le poids doit être entre 30 et 300 kg"
                    return ConversationState.GOAL_COLLECTION, None
                except ValueError:
                    return current_state, "Veuillez entrer un nombre valide pour votre poids"
                    
            # Collecte du poids cible
            if current_state == ConversationState.GOAL_COLLECTION:
                try:
                    target = float(message.strip())
                    if target < 30 or target > 300:
                        return current_state, "Le poids cible doit être entre 30 et 300 kg"
                    return ConversationState.TARGET_DATE_COLLECTION, None
                except ValueError:
                    return current_state, "Veuillez entrer un nombre valide pour votre poids cible"
                    
            # Collecte de la date cible
            if current_state == ConversationState.TARGET_DATE_COLLECTION:
                if not self._validate_date_format(message):
                    return current_state, "Veuillez entrer une date au format AAAA-MM-JJ"
                return ConversationState.DIET_PREFERENCES, None
                
            # Collecte des préférences alimentaires
            if current_state == ConversationState.DIET_PREFERENCES:
                return ConversationState.DIET_RESTRICTIONS, None
                
            # Collecte des restrictions alimentaires
            if current_state == ConversationState.DIET_RESTRICTIONS:
                return ConversationState.PLAN_GENERATION, None
                
            # Génération et revue du plan
            if current_state == ConversationState.PLAN_GENERATION:
                return ConversationState.PLAN_REVIEW, None
                
            if current_state == ConversationState.PLAN_REVIEW:
                return ConversationState.FREE_CHAT, None
                
            # Par défaut, rester en chat libre
            return ConversationState.FREE_CHAT, None
            
        except Exception as e:
            logger.error(f"Erreur dans la transition d'état: {str(e)}")
            return current_state, "Une erreur est survenue. Veuillez réessayer."

    def _extract_language(self, message: str) -> Optional[str]:
        """Extrait la préférence de langue du message."""
        msg_lower = message.lower()
        if "french" in msg_lower or "français" in msg_lower:
            return "fr"
        if "english" in msg_lower or "anglais" in msg_lower:
            return "en"
        return None

    def _validate_date_format(self, date_str: str) -> bool:
        """Valide le format de date (AAAA-MM-JJ)."""
        try:
            datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def extract_and_validate_field(self, current_state: ConversationState, message: str, profile_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extrait et valide une valeur de champ basée sur l'état actuel.
        
        Args:
            current_state: État actuel de la conversation
            message: Message de l'utilisateur
            profile_data: Données actuelles du profil
            
        Returns:
            Dictionnaire avec les données validées ou None si invalide
        """
        try:
            # Nettoyer le message
            value = message.strip().upper()
            
            # Gestion spéciale pour la sélection de langue
            if current_state == ConversationState.LANGUAGE_SELECTION:
                if value in ["FR", "FRANÇAIS", "FRENCH"]:
                    return {"language": "fr"}
                elif value in ["EN", "ENGLISH", "ANGLAIS"]:
                    return {"language": "en"}
                return None
                
            # Pour les autres champs, nettoyer la valeur
            value = message.strip()
            
            # Mapper les états aux champs de la base de données
            state_to_field = {
                ConversationState.NAME_COLLECTION: "first_name",
                ConversationState.AGE_COLLECTION: "age",
                ConversationState.HEIGHT_COLLECTION: "height_cm",
                ConversationState.START_WEIGHT_COLLECTION: "start_weight",
                ConversationState.GOAL_COLLECTION: "target_weight",
                ConversationState.TARGET_DATE_COLLECTION: "target_date"
            }
            
            field = state_to_field.get(current_state)
            if not field:
                logger.error(f"No field mapping for state: {current_state}")
                return None
                
            # Valider et convertir selon le type de champ
            if field == "first_name":
                if not value or len(value) < 2:
                    return None
                return {"first_name": value}
                
            elif field == "age":
                try:
                    age = int(value)
                    if age < 12 or age > 100:
                        return None
                    return {"age": age}
                except ValueError:
                    return None
                    
            elif field == "height_cm":
                try:
                    height = int(value)
                    if height < 100 or height > 250:
                        return None
                    return {"height_cm": height}
                except ValueError:
                    return None
                    
            elif field in ["start_weight", "target_weight"]:
                try:
                    weight = float(value)
                    if weight < 30 or weight > 300:
                        return None
                    return {field: weight}
                except ValueError:
                    return None
                    
            elif field == "target_date":
                try:
                    from datetime import datetime, date
                    target_date = datetime.strptime(value, "%Y-%m-%d").date()
                    today = date.today()
                    
                    # Vérifier que la date est dans le futur mais pas trop loin
                    if target_date <= today:
                        return None
                    if (target_date - today).days > 730:  # 2 ans max
                        return None
                        
                    return {"target_date": value}  # Garder le format string pour la BD
                except ValueError:
                    return None
                    
            return None
            
        except Exception as e:
            logger.error(f"Error extracting field value: {str(e)}")
            return None

# Instance globale
flow_manager = FlowManager() 