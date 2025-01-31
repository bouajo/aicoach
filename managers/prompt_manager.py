"""
Génère des prompts dynamiques en fonction de l'état et du profil.
"""

from typing import Dict, Any, Optional
from data.models import UserProfile, DietPlan, ConversationState

class PromptManager:
    """Gère les prompts système et les templates de messages."""
    
    def __init__(self):
        self.system_prompts = {
            "base": {
                "fr": (
                    "Tu es Eric, un coach en nutrition professionnel avec plus de 20 ans d'expérience. "
                    "Tu aides les gens à atteindre leurs objectifs de santé et de forme physique grâce à "
                    "des conseils nutritionnels personnalisés. Sois amical, professionnel et concis. "
                    "Concentre-toi sur la collecte des informations nécessaires avant de faire des recommandations."
                ),
                "en": (
                    "You are Eric, a professional nutrition coach with over 20 years of experience. "
                    "You help people achieve their health and fitness goals through personalized nutrition advice. "
                    "Be friendly, professional, and concise. Focus on gathering necessary information "
                    "before making recommendations."
                )
            },
            "data_collection": {
                "en": (
                    "You are now in data collection mode. Ask one question at a time to gather the following "
                    "information: age, height (in cm), current weight (in kg), target weight (in kg), and "
                    "target date. Validate each response before moving to the next question."
                ),
                "fr": (
                    "Tu es maintenant en mode collecte de données. Pose une question à la fois pour recueillir "
                    "les informations suivantes : âge, taille (en cm), poids actuel (en kg), poids cible (en kg) "
                    "et date cible. Valide chaque réponse avant de passer à la question suivante."
                )
            },
            "diet_planning": {
                "en": (
                    "You are now in diet planning mode. Based on the user's profile and goals, create a "
                    "personalized diet plan. Consider their current weight, target weight, and timeline. "
                    "Ask about any dietary restrictions or preferences before finalizing the plan."
                ),
                "fr": (
                    "Tu es maintenant en mode planification alimentaire. En fonction du profil et des objectifs "
                    "de l'utilisateur, crée un plan alimentaire personnalisé. Prends en compte leur poids actuel, "
                    "poids cible et délai. Demande les restrictions ou préférences alimentaires avant de "
                    "finaliser le plan."
                )
            }
        }
        
        self.message_templates = {
            ConversationState.INTRODUCTION: {
                "fr": (
                    "👋 Hello! I'm Eric, your personal nutrition coach.\n\n"
                    "To begin our journey together, please tell me which language you would like to communicate in.\n\n"
                    "For example, you can write: English, Français, etc."
                ),
                "en": (
                    "👋 Hello! I'm Eric, your personal nutrition coach.\n\n"
                    "To begin our journey together, please tell me which language you would like to communicate in.\n\n"
                    "For example, you can write: English, Français, etc."
                )
            },
            ConversationState.LANGUAGE_CONFIRMATION: {
                "fr": "✅ Parfait! Nous continuerons en français. Pour commencer, j'aimerais en savoir plus sur vous.",
                "en": "✅ Perfect! We'll continue in English. To begin, I'd like to learn more about you."
            },
            ConversationState.NAME_COLLECTION: {
                "fr": "👤 Quel est votre prénom ?",
                "en": "👤 What is your first name?"
            },
            ConversationState.AGE_COLLECTION: {
                "fr": "🎂 {first_name}, quel âge avez-vous ?",
                "en": "🎂 {first_name}, how old are you?"
            },
            ConversationState.HEIGHT_COLLECTION: {
                "fr": "📏 Quelle est votre taille en centimètres ?",
                "en": "📏 What is your height in centimeters?"
            },
            ConversationState.START_WEIGHT_COLLECTION: {
                "fr": "⚖️ Quel est votre poids actuel en kilogrammes ?",
                "en": "⚖️ What is your current weight in kilograms?"
            },
            ConversationState.GOAL_COLLECTION: {
                "fr": "🎯 Quel est votre poids cible en kilogrammes ?",
                "en": "🎯 What is your target weight in kilograms?"
            },
            ConversationState.TARGET_DATE_COLLECTION: {
                "fr": (
                    "📅 Quand souhaitez-vous atteindre cet objectif ?\n"
                    "Format: AAAA-MM-JJ (exemple: 2024-12-31)"
                ),
                "en": (
                    "📅 When would you like to achieve this goal?\n"
                    "Format: YYYY-MM-DD (example: 2024-12-31)"
                )
            },
            ConversationState.DIET_PREFERENCES: {
                "fr": (
                    "Avez-vous des préférences alimentaires ? Par exemple :\n"
                    "- Végétarien/Végétalien\n"
                    "- Riche en protéines\n"
                    "- Pauvre en glucides\n"
                    "- Régime méditerranéen"
                ),
                "en": (
                    "Do you have any dietary preferences? For example:\n"
                    "- Vegetarian/Vegan\n"
                    "- High protein\n"
                    "- Low carb\n"
                    "- Mediterranean diet"
                )
            },
            ConversationState.DIET_RESTRICTIONS: {
                "fr": (
                    "Avez-vous des restrictions alimentaires ou des allergies ?\n"
                    "Par exemple :\n"
                    "- Intolérance au gluten\n"
                    "- Intolérance au lactose\n"
                    "- Allergies aux noix\n"
                    "- Autres allergies alimentaires"
                ),
                "en": (
                    "Do you have any dietary restrictions or allergies?\n"
                    "For example:\n"
                    "- Gluten intolerance\n"
                    "- Lactose intolerance\n"
                    "- Nut allergies\n"
                    "- Other food allergies"
                )
            }
        }

    def get_system_prompt(self, prompt_type: str = "base", language: str = "fr") -> str:
        """Récupère le prompt système pour le type et la langue donnés."""
        return self.system_prompts.get(prompt_type, {}).get(language, self.system_prompts["base"][language])

    def get_message_template(
        self,
        state: ConversationState,
        language: str = "fr",
        **kwargs
    ) -> str:
        """Récupère le template de message pour l'état et la langue donnés."""
        template = self.message_templates.get(state, {}).get(language, "")
        if not template:
            # Fallback messages
            fallbacks = {
                "fr": "Je suis désolé, je ne peux pas traiter cette étape pour le moment.",
                "en": "I'm sorry, I cannot process this step at the moment."
            }
            return fallbacks.get(language, fallbacks["fr"])
            
        try:
            if kwargs:
                return template.format(**kwargs)
            return template
        except Exception as e:
            logger.error(f"Error formatting template: {e}")
            return template

    def get_error_message(self, error_type: str, language: str = "fr") -> str:
        """Récupère le message d'erreur pour le type et la langue donnés."""
        error_messages = {
            "invalid_age": {
                "fr": "Veuillez fournir un âge valide entre 12 et 100 ans.",
                "en": "Please provide a valid age between 12 and 100."
            },
            "invalid_height": {
                "fr": "Veuillez fournir une taille valide en centimètres (entre 100 et 250).",
                "en": "Please provide a valid height in centimeters (between 100 and 250)."
            },
            "invalid_weight": {
                "fr": "Veuillez fournir un poids valide en kilogrammes (entre 30 et 300).",
                "en": "Please provide a valid weight in kilograms (between 30 and 300)."
            },
            "invalid_date": {
                "fr": "Veuillez fournir une date valide au format AAAA-MM-JJ.",
                "en": "Please provide a valid date in YYYY-MM-DD format."
            }
        }
        return error_messages.get(error_type, {}).get(language, "Une erreur s'est produite.")

    def get_summary_prompt(self, profile: UserProfile, plan: Optional[DietPlan] = None, language: str = "fr") -> str:
        """Génère un résumé du profil et du plan."""
        if language == "fr":
            summary = (
                f"Récapitulatif de votre profil :\n"
                f"- Âge : {profile.age} ans\n"
                f"- Taille : {profile.height_cm} cm\n"
                f"- Poids actuel : {profile.current_weight} kg\n"
                f"- Objectif : {profile.target_weight} kg\n"
                f"- Date cible : {profile.target_date}\n"
            )
            if plan:
                summary += (
                    f"\nVotre plan alimentaire :\n"
                    f"- Calories quotidiennes : {plan.daily_calories} kcal\n"
                    f"- Fréquence des repas : {plan.meal_frequency} fois par jour\n"
                )
            return summary + "\nSouhaitez-vous des détails supplémentaires ou des ajustements ?"
        else:
            summary = (
                f"Your profile summary:\n"
                f"- Age: {profile.age} years\n"
                f"- Height: {profile.height_cm} cm\n"
                f"- Current weight: {profile.current_weight} kg\n"
                f"- Target: {profile.target_weight} kg\n"
                f"- Target date: {profile.target_date}\n"
            )
            if plan:
                summary += (
                    f"\nYour diet plan:\n"
                    f"- Daily calories: {plan.daily_calories} kcal\n"
                    f"- Meal frequency: {plan.meal_frequency} times per day\n"
                )
            return summary + "\nWould you like additional details or adjustments?"

    def get_introduction_prompt(self, language: str = "fr") -> str:
        """Get the initial introduction prompt in the specified language."""
        return self.message_templates[ConversationState.INTRODUCTION][language]

    def get_data_collection_prompt(self, field: str, language: str = "fr") -> str:
        """Get the prompt for collecting a specific piece of user data."""
        state = getattr(ConversationState, f"{field.upper()}_COLLECTION", None)
        if state and state in self.message_templates:
            return self.message_templates[state][language]
        return self.get_error_message("invalid_field", language)

    def get_validation_error(self, field: str, language: str = "fr") -> str:
        """Get error message for field validation failure."""
        errors = {
            "first_name": {
                "fr": "Veuillez entrer un prénom valide.",
                "en": "Please enter a valid first name."
            },
            "age": {
                "fr": "Veuillez entrer un âge valide entre 12 et 100 ans.",
                "en": "Please enter a valid age between 12 and 100 years."
            },
            "height_cm": {
                "fr": "Veuillez entrer une taille valide entre 100 et 250 cm.",
                "en": "Please enter a valid height between 100 and 250 cm."
            },
            "current_weight": {
                "fr": "Veuillez entrer un poids valide entre 30 et 300 kg.",
                "en": "Please enter a valid weight between 30 and 300 kg."
            },
            "target_weight": {
                "fr": "Veuillez entrer un poids cible valide entre 30 et 300 kg.",
                "en": "Please enter a valid target weight between 30 and 300 kg."
            },
            "target_date": {
                "fr": "Veuillez entrer une date future valide au format AAAA-MM-JJ (maximum 2 ans).",
                "en": "Please enter a valid future date in YYYY-MM-DD format (maximum 2 years)."
            }
        }
        return errors.get(field, {}).get(language, "Une erreur s'est produite.")

# Instance globale
prompt_manager = PromptManager()