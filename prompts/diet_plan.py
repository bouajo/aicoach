"""
Prompts pour la génération de plans alimentaires.
"""

from typing import Dict, Any
from datetime import datetime, date

def get_diet_plan_prompt(user_data: Dict[str, Any], language: str = "fr") -> str:
    """
    Génère un prompt pour la création d'un plan alimentaire.
    
    Args:
        user_data: Données du profil utilisateur
        language: Langue préférée (en/fr)
        
    Returns:
        Prompt pour la génération du plan
    """
    if language == "fr":
        return _get_french_prompt(user_data)
    return _get_english_prompt(user_data)

def _get_french_prompt(user_data: Dict[str, Any]) -> str:
    """Génère le prompt en français."""
    name = user_data.get("first_name", "l'utilisateur")
    current_weight = user_data.get("current_weight")
    target_weight = user_data.get("target_weight")
    target_date = user_data.get("target_date")
    height_cm = user_data.get("height_cm")
    age = user_data.get("age")
    preferences = user_data.get("diet_preferences", [])
    restrictions = user_data.get("diet_restrictions", [])
    
    # Calcul de la différence de poids et du délai
    weight_diff = target_weight - current_weight if all([target_weight, current_weight]) else None
    days_left = None
    if isinstance(target_date, (str, date)):
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        days_left = (target_date - datetime.now().date()).days
    
    prompt = f"""
En tant que coach diététique professionnel, créez un plan alimentaire personnalisé pour {name} basé sur les informations suivantes :

Profil :
- Âge : {age} ans
- Taille : {height_cm} cm
- Poids actuel : {current_weight} kg
- Poids cible : {target_weight} kg"""

    if days_left is not None:
        prompt += f"\n- Délai : {days_left} jours"
    if weight_diff is not None:
        prompt += f"\n- Objectif : {weight_diff:+.1f} kg"
        
    if preferences:
        prompt += "\n\nPréférences alimentaires :\n" + "\n".join(f"- {p}" for p in preferences)
    if restrictions:
        prompt += "\n\nRestrictions alimentaires :\n" + "\n".join(f"- {r}" for r in restrictions)
        
    prompt += """

Calculez et incluez :
1. Besoins caloriques quotidiens (métabolisme de base + niveau d'activité)
2. Répartition des macronutriments (protéines, glucides, lipides)
3. Fréquence et timing des repas
4. Types d'aliments à privilégier
5. Aliments à éviter ou à limiter
6. Recommandations d'hydratation
7. Suggestions de compléments (si nécessaire)

Prenez en compte :
- Un rythme de perte/gain de poids sain et durable
- Les besoins nutritionnels adaptés à l'âge
- L'importance des protéines pour le maintien musculaire
- Le rôle des fibres et des micronutriments

Fournissez :
1. Une explication claire du plan
2. Des idées de repas types
3. Des conseils pour réussir
4. Les signes d'alerte à surveiller
5. Quand et comment ajuster le plan

Gardez un ton professionnel mais amical, et soulignez l'importance des changements sains et durables."""

    return prompt

def _get_english_prompt(user_data: Dict[str, Any]) -> str:
    """Génère le prompt en anglais."""
    name = user_data.get("first_name", "the user")
    current_weight = user_data.get("current_weight")
    target_weight = user_data.get("target_weight")
    target_date = user_data.get("target_date")
    height_cm = user_data.get("height_cm")
    age = user_data.get("age")
    preferences = user_data.get("diet_preferences", [])
    restrictions = user_data.get("diet_restrictions", [])
    
    # Calculate weight difference and timeline
    weight_diff = target_weight - current_weight if all([target_weight, current_weight]) else None
    days_left = None
    if isinstance(target_date, (str, date)):
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        days_left = (target_date - datetime.now().date()).days
    
    prompt = f"""
As a professional diet coach, create a personalized diet plan for {name} based on the following information:

Profile:
- Age: {age} years
- Height: {height_cm} cm
- Current weight: {current_weight} kg
- Target weight: {target_weight} kg"""

    if days_left is not None:
        prompt += f"\n- Timeline: {days_left} days"
    if weight_diff is not None:
        prompt += f"\n- Goal: {weight_diff:+.1f} kg"
        
    if preferences:
        prompt += "\n\nDietary preferences:\n" + "\n".join(f"- {p}" for p in preferences)
    if restrictions:
        prompt += "\n\nDietary restrictions:\n" + "\n".join(f"- {r}" for r in restrictions)
        
    prompt += """

Calculate and include:
1. Daily caloric needs (BMR + activity level)
2. Macronutrient distribution (protein, carbs, fat)
3. Meal frequency and timing
4. Types of foods to focus on
5. Foods to avoid or limit
6. Hydration recommendations
7. Supplement suggestions (if necessary)

Consider:
- A healthy and sustainable rate of weight change
- Age-appropriate nutritional needs
- The importance of protein for muscle maintenance
- The role of fiber and micronutrients

Provide:
1. A clear explanation of the plan
2. Sample meal ideas
3. Tips for success
4. Warning signs to watch for
5. When and how to adjust the plan

Keep the tone professional but friendly, and emphasize the importance of sustainable, healthy changes."""

    return prompt 