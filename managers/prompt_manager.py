"""
Manages dynamic prompt generation based on conversation state and context.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from data.models import (
    ConversationState,
    UserProfile,
    ConversationMessage,
    DietPlan
)

logger = logging.getLogger(__name__)

class PromptManager:
    def __init__(self):
        # Message d'introduction détaillé
        self.initial_greeting = (
            "Bonjour ! Je suis Eric, votre coach en nutrition personnalisé. 👋\n\n"
            "Je suis là pour vous aider à atteindre vos objectifs de manière saine et durable. "
            "Pour créer un programme adapté à vos besoins, j'ai besoin de quelques informations :\n"
            "- Votre âge\n"
            "- Votre taille\n"
            "- Votre poids actuel\n"
            "- Votre poids idéal\n"
            "- Le temps que vous vous donnez pour l'atteindre\n\n"
            "Pour commencer, pouvez-vous me dire votre âge ?"
        )

        # Prompts de base pour chaque étape
        self.system_prompts = {
            "base_identity": """
Tu es Eric, coach en nutrition professionnel. Tu collectes les informations de manière naturelle et bienveillante.
- Sois empathique et à l'écoute
- Pose UNE SEULE question à la fois
- Garde un ton amical mais professionnel
- Encourage et valorise chaque réponse
""",
            "data_collection": {
                "age": {
                    "question": "Quel est votre âge ?",
                    "validation": "Nombre entre 16 et 100",
                    "next": "height"
                },
                "height": {
                    "question": "Merci ! Et quelle est votre taille (en cm) ?",
                    "validation": "Nombre entre 140 et 220",
                    "next": "current_weight"
                },
                "current_weight": {
                    "question": "D'accord, et quel est votre poids actuel (en kg) ?",
                    "validation": "Nombre entre 40 et 250",
                    "next": "target_weight"
                },
                "target_weight": {
                    "question": "Très bien. Quel est votre objectif de poids (en kg) ?",
                    "validation": "Nombre entre 40 et 250",
                    "next": "target_date"
                },
                "target_date": {
                    "question": "Dans combien de mois souhaitez-vous atteindre cet objectif ?",
                    "validation": "Nombre entre 1 et 24",
                    "next": "summary"
                }
            },
            "data_validation": """
Vérifie si la réponse est valide selon les critères.
Si non valide, explique gentiment pourquoi et redemande l'information.
Si valide, passe à la question suivante avec une transition naturelle.
""",
            "summary_creation": """
Une fois toutes les informations collectées, crée un résumé personnalisé :
1. Récapitule les informations fournies
2. Calcule l'IMC actuel
3. Détermine si l'objectif est réaliste
4. Propose une approche adaptée
"""
        }

    def get_initial_greeting(self) -> str:
        """Retourne le message d'introduction initial."""
        return self.initial_greeting

    def get_data_collection_prompt(self, current_field: str, profile: UserProfile, last_answer: str = "") -> str:
        """
        Génère le prompt pour la collecte de données.
        """
        field_info = self.system_prompts["data_collection"].get(current_field, {})
        profile_summary = self._generate_profile_summary(profile)
        
        return f"""
{self.system_prompts['base_identity']}

État actuel de la collecte :
{profile_summary}

Dernière réponse de l'utilisateur : "{last_answer}"

Information à collecter : {current_field}
Validation requise : {field_info.get('validation', 'N/A')}

Si la réponse est valide :
- Stocke l'information
- Pose la question suivante : {field_info.get('question', 'Passez à la suite')}

Si la réponse n'est pas valide :
- Explique gentiment pourquoi
- Redemande l'information de manière bienveillante
"""

    def get_summary_prompt(self, profile: UserProfile, diet_plan: Optional[DietPlan] = None) -> str:
        """
        Génère le prompt pour le résumé des informations collectées.
        """
        return f"""
{self.system_prompts['base_identity']}

{self.system_prompts['summary_creation']}

Profil complet :
{self._generate_profile_summary(profile)}

Plan alimentaire actuel :
{self._generate_diet_plan_summary(diet_plan)}

Crée un résumé personnalisé et propose la prochaine étape.
"""

    def _generate_profile_summary(self, profile: UserProfile) -> str:
        """Génère un résumé du profil utilisateur."""
        summary_parts = []
        
        if profile.age:
            summary_parts.append(f"- Âge : {profile.age} ans")
        if profile.height_cm:
            summary_parts.append(f"- Taille : {profile.height_cm} cm")
        if profile.current_weight:
            summary_parts.append(f"- Poids actuel : {profile.current_weight} kg")
        if profile.target_weight:
            summary_parts.append(f"- Poids cible : {profile.target_weight} kg")
            
        return "\n".join(summary_parts) if summary_parts else "Aucune information collectée"

    def _generate_diet_plan_summary(self, diet_plan: Optional[DietPlan]) -> str:
        """Génère un résumé du plan alimentaire."""
        if not diet_plan:
            return "Plan non défini"
            
        return f"Plan alimentaire : {diet_plan.calories_per_day} kcal/jour"

# Instance globale du PromptManager
prompt_manager = PromptManager()