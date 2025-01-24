from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime

class UserInput(BaseModel):
    first_name: str
    age: Optional[int] = None
    height: Optional[int] = None
    current_weight: Optional[float] = None
    target_weight: Optional[float] = None
    target_date: Optional[str] = None

    @validator('first_name')
    def validate_name(cls, v):
        v = v.strip()
        if not v or not any(c.isalpha() for c in v):
            raise ValueError("Le prénom doit contenir au moins une lettre")
        return v.title()

    @validator('age')
    def validate_age(cls, v):
        if v is not None and not (12 <= v <= 100):
            raise ValueError("L'âge doit être compris entre 12 et 100 ans")
        return v

    @validator('height')
    def validate_height(cls, v):
        if v is not None and not (100 <= v <= 250):
            raise ValueError("La taille doit être comprise entre 100 et 250 cm")
        return v

    @validator('current_weight', 'target_weight')
    def validate_weight(cls, v):
        if v is not None and not (30 <= v <= 300):
            raise ValueError("Le poids doit être compris entre 30 et 300 kg")
        return v

    @validator('target_date')
    def validate_date(cls, v):
        if v is not None:
            try:
                date = datetime.strptime(v, "%Y-%m-%d")
                if date < datetime.now():
                    raise ValueError("La date cible doit être dans le futur")
            except ValueError as e:
                raise ValueError("Format de date invalide. Utilisez YYYY-MM-DD")
        return v 