"""
Prompts pour l'introduction et la collecte initiale de données.
"""

from typing import Dict, Any, Optional
from datetime import datetime

def get_introduction_prompt(language: str = "fr") -> str:
    """
    Génère le prompt d'introduction initial.
    
    Args:
        language: Langue préférée (en/fr)
        
    Returns:
        Prompt d'introduction
    """
    if language == "fr":
        return (
            "Bonjour ! Je suis Eric, votre coach en nutrition personnel avec plus de 20 ans "
            "d'expérience. Je suis là pour vous aider à atteindre vos objectifs de santé et "
            "de forme physique de manière saine et durable.\n\n"
            "Pour créer un programme parfaitement adapté à vos besoins, j'aurai besoin de "
            "quelques informations :\n"
            "- Votre âge\n"
            "- Votre taille\n"
            "- Votre poids actuel\n"
            "- Votre poids cible\n"
            "- Le délai que vous vous donnez\n\n"
            "Préférez-vous continuer en français ou en anglais ? (Tapez 'Français' ou 'English')"
        )
    return (
        "Hello! I'm Eric, your personal nutrition coach with over 20 years of experience. "
        "I'm here to help you achieve your health and fitness goals in a healthy and "
        "sustainable way.\n\n"
        "To create a program perfectly tailored to your needs, I'll need some information:\n"
        "- Your age\n"
        "- Your height\n"
        "- Your current weight\n"
        "- Your target weight\n"
        "- Your timeline\n\n"
        "Would you prefer to continue in English or French? (Type 'English' or 'French')"
    )

def get_data_collection_prompt(field: str, language: str = "fr", context: Optional[Dict[str, Any]] = None) -> str:
    """
    Génère un prompt pour la collecte d'une donnée spécifique.
    
    Args:
        field: Champ à collecter
        language: Langue préférée (en/fr)
        context: Contexte optionnel pour personnalisation
        
    Returns:
        Prompt de collecte de données
    """
    name = context.get("first_name", "") if context else ""
    
    prompts = {
        "first_name": {
            "fr": "Pour commencer, quel est votre prénom ?",
            "en": "To get started, what's your first name?"
        },
        "age": {
            "fr": f"Ravi de vous rencontrer{f', {name}' if name else ''} ! Quel âge avez-vous ?",
            "en": f"Nice to meet you{f', {name}' if name else ''}! How old are you?"
        },
        "height_cm": {
            "fr": "Quelle est votre taille en centimètres ?",
            "en": "What is your height in centimeters?"
        },
        "current_weight": {
            "fr": "Quel est votre poids actuel en kilogrammes ?",
            "en": "What is your current weight in kilograms?"
        },
        "target_weight": {
            "fr": "Quel est votre poids cible en kilogrammes ?",
            "en": "What is your target weight in kilograms?"
        },
        "target_date": {
            "fr": "Quand souhaitez-vous atteindre cet objectif ? (Format: AAAA-MM-JJ)",
            "en": "When would you like to achieve this goal? (Format: YYYY-MM-DD)"
        },
        "diet_preferences": {
            "fr": (
                "Avez-vous des préférences alimentaires ? Par exemple :\n"
                "- Végétarien/Végétalien\n"
                "- Riche en protéines\n"
                "- Pauvre en glucides\n"
                "- Régime méditerranéen\n\n"
                "Décrivez vos préférences ou tapez 'aucune'."
            ),
            "en": (
                "Do you have any dietary preferences? For example:\n"
                "- Vegetarian/Vegan\n"
                "- High protein\n"
                "- Low carb\n"
                "- Mediterranean diet\n\n"
                "Describe your preferences or type 'none'."
            )
        },
        "diet_restrictions": {
            "fr": (
                "Avez-vous des restrictions alimentaires ou des allergies ? Par exemple :\n"
                "- Intolérance au gluten\n"
                "- Intolérance au lactose\n"
                "- Allergies aux noix\n"
                "- Autres allergies alimentaires\n\n"
                "Listez vos restrictions ou tapez 'aucune'."
            ),
            "en": (
                "Do you have any dietary restrictions or allergies? For example:\n"
                "- Gluten intolerance\n"
                "- Lactose intolerance\n"
                "- Nut allergies\n"
                "- Other food allergies\n\n"
                "List your restrictions or type 'none'."
            )
        }
    }
    
    return prompts.get(field, {}).get(language, f"Veuillez fournir votre {field} :" if language == "fr" else f"Please provide your {field}:") 