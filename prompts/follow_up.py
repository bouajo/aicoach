"""
Prompts pour le suivi et les ajustements du plan.
"""

from typing import Dict, Any, Optional
from datetime import datetime, date

def get_progress_check_prompt(user_data: Dict[str, Any], language: str = "fr") -> str:
    """
    Génère un prompt pour vérifier les progrès de l'utilisateur.
    
    Args:
        user_data: Données du profil utilisateur
        language: Langue préférée (en/fr)
        
    Returns:
        Prompt pour le suivi des progrès
    """
    if language == "fr":
        return _get_french_progress_prompt(user_data)
    return _get_english_progress_prompt(user_data)

def get_adjustment_prompt(user_data: Dict[str, Any], language: str = "fr") -> str:
    """
    Génère un prompt pour ajuster le plan en fonction des progrès.
    
    Args:
        user_data: Données du profil et progrès utilisateur
        language: Langue préférée (en/fr)
        
    Returns:
        Prompt pour l'ajustement du plan
    """
    if language == "fr":
        return _get_french_adjustment_prompt(user_data)
    return _get_english_adjustment_prompt(user_data)

def _get_french_progress_prompt(user_data: Dict[str, Any]) -> str:
    """Génère le prompt de suivi en français."""
    name = user_data.get("first_name", "l'utilisateur")
    start_weight = user_data.get("current_weight")
    target_weight = user_data.get("target_weight")
    target_date = user_data.get("target_date")
    
    # Calcul du temps restant
    time_remaining = ""
    if isinstance(target_date, (str, date)):
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        days_left = (target_date - datetime.now().date()).days
        if days_left > 0:
            time_remaining = f"\n- Temps restant : {days_left} jours"
    
    return f"""
En tant que coach diététique professionnel, vérifions les progrès de {name} :

Plan initial :
- Poids de départ : {start_weight} kg
- Poids cible : {target_weight} kg{time_remaining}

Demandez à propos de :
1. Poids et mesures actuels
2. Niveaux d'énergie et humeur
3. Respect du plan alimentaire
4. Difficultés ou défis rencontrés
5. Changements dans la routine d'exercice
6. Qualité du sommeil
7. Niveaux de stress
8. Nouveaux problèmes de santé éventuels

Basé sur leurs réponses :
1. Calculez le taux de progression
2. Évaluez si des ajustements sont nécessaires
3. Fournissez des retours spécifiques
4. Proposez des solutions aux défis
5. Apportez un soutien motivationnel

Gardez un ton encourageant et concentrez-vous sur les progrès durables plutôt que sur les résultats rapides."""

def _get_english_progress_prompt(user_data: Dict[str, Any]) -> str:
    """Génère le prompt de suivi en anglais."""
    name = user_data.get("first_name", "the user")
    start_weight = user_data.get("current_weight")
    target_weight = user_data.get("target_weight")
    target_date = user_data.get("target_date")
    
    # Calculate time remaining
    time_remaining = ""
    if isinstance(target_date, (str, date)):
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        days_left = (target_date - datetime.now().date()).days
        if days_left > 0:
            time_remaining = f"\n- Time remaining: {days_left} days"
    
    return f"""
As a professional diet coach, let's check {name}'s progress:

Initial Plan:
- Starting weight: {start_weight} kg
- Target weight: {target_weight} kg{time_remaining}

Ask about:
1. Current weight and measurements
2. Energy levels and mood
3. Adherence to the meal plan
4. Any challenges or difficulties
5. Exercise routine changes
6. Sleep quality
7. Stress levels
8. Any new health concerns

Based on their responses:
1. Calculate progress rate
2. Assess if adjustments are needed
3. Provide specific feedback
4. Offer solutions to challenges
5. Give motivational support

Keep the tone encouraging and focus on sustainable progress rather than quick results."""

def _get_french_adjustment_prompt(user_data: Dict[str, Any]) -> str:
    """Génère le prompt d'ajustement en français."""
    name = user_data.get("first_name", "l'utilisateur")
    current_calories = user_data.get("daily_calories")
    progress_rate = user_data.get("progress_rate", 0)  # kg par semaine
    
    return f"""
En tant que coach diététique professionnel, créons un plan ajusté pour {name} basé sur leurs progrès :

Plan actuel :
- Calories quotidiennes : {current_calories} kcal
- Taux de progression : {progress_rate} kg/semaine

Considérez :
1. Si le taux de progression actuel est sain
2. Si les ratios de macronutriments nécessitent des ajustements
3. L'optimisation du timing des repas
4. La qualité et la variété des aliments
5. Les niveaux d'hydratation
6. Les recommandations de compléments
7. L'intégration de l'exercice

Fournissez :
1. Ajustements spécifiques des calories et macros
2. Nouvelles suggestions de repas
3. Modifications de timing si nécessaire
4. Stratégies supplémentaires pour réussir
5. Signes d'alerte à surveiller

Gardez les changements modérés et durables, en vous concentrant sur le succès à long terme."""

def _get_english_adjustment_prompt(user_data: Dict[str, Any]) -> str:
    """Génère le prompt d'ajustement en anglais."""
    name = user_data.get("first_name", "the user")
    current_calories = user_data.get("daily_calories")
    progress_rate = user_data.get("progress_rate", 0)  # kg per week
    
    return f"""
As a professional diet coach, let's create an adjusted plan for {name} based on their progress:

Current Plan:
- Daily calories: {current_calories} kcal
- Progress rate: {progress_rate} kg/week

Consider:
1. Whether the current rate of progress is healthy
2. If macronutrient ratios need adjustment
3. Meal timing optimization
4. Food quality and variety
5. Hydration levels
6. Supplement recommendations
7. Exercise integration

Provide:
1. Specific calorie and macro adjustments
2. New meal suggestions
3. Timing modifications if needed
4. Additional strategies for success
5. Warning signs to watch for

Keep the changes moderate and sustainable, focusing on long-term success.""" 