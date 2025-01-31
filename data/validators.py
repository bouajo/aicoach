"""
Validateurs de données pour les profils utilisateurs et plans alimentaires.
"""

from typing import Dict, Any, Optional
from datetime import datetime, date

def validate_user_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valide et nettoie les données du profil utilisateur.
    
    Args:
        data: Dictionnaire contenant les données du profil
        
    Returns:
        Données nettoyées et validées
    """
    cleaned = {}
    
    # Required fields
    if "user_id" not in data:
        raise ValueError("user_id is required")
    cleaned["user_id"] = str(data["user_id"])
    
    # Optional fields with validation
    if "first_name" in data:
        cleaned["first_name"] = str(data["first_name"]) if data["first_name"] else None
        
    if "language" in data:
        lang = data["language"]
        if lang and lang not in ["en", "fr"]:
            raise ValueError("language must be 'en' or 'fr'")
        cleaned["language"] = lang
        
    if "age" in data:
        age = data["age"]
        if age is not None:
            if not isinstance(age, int) or age < 12 or age > 100:
                raise ValueError("age must be between 12 and 100")
            cleaned["age"] = age
            
    if "height_cm" in data:
        height = data["height_cm"]
        if height is not None:
            if not isinstance(height, int) or height < 100 or height > 250:
                raise ValueError("height_cm must be between 100 and 250")
            cleaned["height_cm"] = height
            
    if "current_weight" in data:
        weight = data["current_weight"]
        if weight is not None:
            if not isinstance(weight, (int, float)) or weight < 30 or weight > 300:
                raise ValueError("current_weight must be between 30 and 300")
            cleaned["current_weight"] = float(weight)
            
    if "target_weight" in data:
        weight = data["target_weight"]
        if weight is not None:
            if not isinstance(weight, (int, float)) or weight < 30 or weight > 300:
                raise ValueError("target_weight must be between 30 and 300")
            cleaned["target_weight"] = float(weight)
            
    if "target_date" in data:
        target_date = data["target_date"]
        if target_date:
            if isinstance(target_date, str):
                try:
                    target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
                except ValueError:
                    raise ValueError("target_date must be in YYYY-MM-DD format")
            elif not isinstance(target_date, date):
                raise ValueError("target_date must be a date object or YYYY-MM-DD string")
            
            # Validate date is in the future but not too far
            today = datetime.now().date()
            if target_date <= today:
                raise ValueError("target_date must be in the future")
            if (target_date - today).days > 730:  # 2 years
                raise ValueError("target_date cannot be more than 2 years in the future")
                
            cleaned["target_date"] = target_date
            
    if "conversation_state" in data:
        cleaned["conversation_state"] = str(data["conversation_state"])
        
    return cleaned

def validate_diet_plan(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valide et nettoie les données du plan alimentaire.
    
    Args:
        data: Dictionnaire contenant les données du plan
        
    Returns:
        Données nettoyées et validées
    """
    cleaned = {}
    
    # Required fields
    if "user_id" not in data:
        raise ValueError("user_id is required")
    cleaned["user_id"] = str(data["user_id"])
    
    # Optional fields with validation
    if "daily_calories" in data:
        calories = data["daily_calories"]
        if calories is not None:
            if not isinstance(calories, int) or calories < 1200 or calories > 4000:
                raise ValueError("daily_calories must be between 1200 and 4000")
            cleaned["daily_calories"] = calories
            
    for ratio in ["protein_ratio", "carbs_ratio", "fat_ratio"]:
        if ratio in data:
            value = data[ratio]
            if value is not None:
                if not isinstance(value, (int, float)) or value < 0 or value > 1:
                    raise ValueError(f"{ratio} must be between 0 and 1")
                cleaned[ratio] = float(value)
                
    if "meal_frequency" in data:
        freq = data["meal_frequency"]
        if freq is not None:
            if not isinstance(freq, int) or freq < 3 or freq > 6:
                raise ValueError("meal_frequency must be between 3 and 6")
            cleaned["meal_frequency"] = freq
            
    if "restrictions" in data:
        restrictions = data["restrictions"]
        if restrictions is not None:
            if not isinstance(restrictions, list):
                raise ValueError("restrictions must be a list")
            cleaned["restrictions"] = [str(r) for r in restrictions]
            
    if "preferences" in data:
        preferences = data["preferences"]
        if preferences is not None:
            if not isinstance(preferences, list):
                raise ValueError("preferences must be a list")
            cleaned["preferences"] = [str(p) for p in preferences]
            
    return cleaned 