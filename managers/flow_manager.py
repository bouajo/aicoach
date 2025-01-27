"""
Manages the conversation flow and question sequencing.
"""

from typing import Dict, Any, Optional, Tuple, List
from data.models import ConversationState
from .state_manager import state_manager
from .prompt_manager import prompt_manager

class FlowManager:
    def __init__(self):
        # Définition de la séquence des questions par état
        self.question_sequence = {
            ConversationState.INTRODUCTION: [
                ("first_name", "prénom"),
                ("age", "âge")
            ],
            ConversationState.COLLECTING_DATA: [
                ("height", "taille (en cm)"),
                ("current_weight", "poids actuel (en kg)"),
                ("target_weight", "poids cible (en kg)"),
                ("target_date", "date objectif (mois/année)")
            ],
            ConversationState.DIET_PLANNING: [
                ("allergies", "allergies ou intolérances alimentaires"),
                ("preferences", "préférences alimentaires")
            ]
        }

        # Validateurs pour chaque type de donnée
        self.validators = {
            "first_name": lambda x: isinstance(x, str) and x.strip() and not any(c.isdigit() for c in x),
            "age": lambda x: isinstance(x, (int, str)) and str(x).isdigit() and 18 <= int(x) <= 100,
            "height": lambda x: isinstance(x, (int, str)) and str(x).isdigit() and 140 <= int(x) <= 220,
            "current_weight": lambda x: isinstance(x, (int, float, str)) and float(str(x)) >= 40 and float(str(x)) <= 300,
            "target_weight": lambda x: isinstance(x, (int, float, str)) and float(str(x)) >= 40 and float(str(x)) <= 300,
            "target_date": lambda x: True  # La validation de la date est gérée séparément
        }

    def process_user_input(self, current_state: ConversationState, user_data: Dict[str, Any], user_message: str) -> Tuple[Dict[str, Any], Optional[str], bool]:
        """
        Traite l'entrée utilisateur et détermine la prochaine action.
        
        Args:
            current_state: État actuel de la conversation
            user_data: Données actuelles de l'utilisateur
            user_message: Message de l'utilisateur
            
        Returns:
            Tuple contenant :
            - Nouvelles données extraites
            - Message d'erreur éventuel
            - Booléen indiquant si la transition d'état est possible
        """
        # Identifie la prochaine donnée attendue
        next_field = self._get_next_expected_field(current_state, user_data)
        if not next_field:
            return {}, None, True  # Toutes les données sont collectées

        field_name, field_description = next_field
        
        # Tente d'extraire et de valider la donnée
        try:
            extracted_value = self._extract_value(field_name, user_message)
            if self._validate_value(field_name, extracted_value):
                return {field_name: extracted_value}, None, self._can_transition(current_state, user_data, field_name, extracted_value)
            else:
                return {}, f"La valeur pour {field_description} n'est pas valide. Veuillez réessayer.", False
        except ValueError as e:
            return {}, str(e), False

    def _get_next_expected_field(self, state: ConversationState, user_data: Dict[str, Any]) -> Optional[Tuple[str, str]]:
        """Détermine la prochaine donnée attendue dans la séquence."""
        if state not in self.question_sequence:
            return None
            
        for field_name, field_description in self.question_sequence[state]:
            if field_name not in user_data or user_data[field_name] is None:
                return field_name, field_description
        return None

    def _extract_value(self, field_name: str, user_message: str) -> Any:
        """Extrait la valeur appropriée du message utilisateur."""
        message = user_message.strip().lower()
        
        if field_name == "first_name":
            return message.capitalize()
            
        elif field_name in ["age", "height"]:
            digits = ''.join(filter(str.isdigit, message))
            if not digits:
                raise ValueError(f"Je n'ai pas trouvé de nombre dans votre réponse.")
            return int(digits)
            
        elif field_name in ["current_weight", "target_weight"]:
            # Extrait le premier nombre (entier ou décimal)
            import re
            matches = re.findall(r'\d+[,.]?\d*', message.replace(',', '.'))
            if not matches:
                raise ValueError(f"Je n'ai pas trouvé de poids dans votre réponse.")
            return float(matches[0])
            
        elif field_name == "target_date":
            # La logique de parsing de date est déjà dans Database.extract_user_data
            # On pourrait la déplacer ici pour plus de cohérence
            return message
            
        return message

    def _validate_value(self, field_name: str, value: Any) -> bool:
        """Valide la valeur extraite."""
        validator = self.validators.get(field_name)
        if not validator:
            return True
        try:
            return validator(value)
        except:
            return False

    def _can_transition(self, current_state: ConversationState, user_data: Dict[str, Any], new_field: str, new_value: Any) -> bool:
        """Vérifie si une transition d'état est possible avec les nouvelles données."""
        # Simule l'ajout de la nouvelle valeur aux données
        updated_data = user_data.copy()
        updated_data[new_field] = new_value
        
        # Vérifie si toutes les données requises pour l'état actuel sont présentes
        required_fields = [field for field, _ in self.question_sequence.get(current_state, [])]
        return all(updated_data.get(field) is not None for field in required_fields)

    def get_next_question(self, state: ConversationState, user_data: Dict[str, Any]) -> Optional[str]:
        """
        Retourne la prochaine question à poser.
        
        Args:
            state: État actuel de la conversation
            user_data: Données actuelles de l'utilisateur
            
        Returns:
            Question à poser ou None si toutes les questions ont été posées
        """
        next_field = self._get_next_expected_field(state, user_data)
        if not next_field:
            return None
            
        field_name, field_description = next_field
        return f"Quel est votre {field_description} ?"

# Instance globale du FlowManager
flow_manager = FlowManager() 