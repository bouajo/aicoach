"""Diet Agent for handling user interactions and profile management."""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json

from services.deepseek_service import deepseek
from data.database import db

logger = logging.getLogger(__name__)

class DietAgent:
    """Agent for handling diet-related interactions."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.required_fields = [
            "first_name",
            "age",
            "height_cm",
            "current_weight",
            "target_weight",
            "activity_level",
            "diet_restrictions",
            "health_conditions"
        ]
        
    async def process_message(self, message_text: str, phone_number: Optional[str] = None) -> str:
        """Process a message from the user."""
        try:
            # Get user profile
            profile = db.get_user_profile(self.user_id)
            if not profile:
                logger.error(f"No profile found for user {self.user_id}")
                return None
                
            # Check if we're in onboarding
            if profile.get("conversation_state") == "onboarding":
                return await self.handle_onboarding(message_text, profile)
                
            # Regular chat processing
            return await self.handle_chat(message_text, profile)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return await self.get_error_message(profile.get("language", "en"))
            
    def initialize_fields_to_ask(self, profile: Dict[str, Any]) -> List[str]:
        """Initialize or get the list of fields that need to be asked."""
        fields_to_ask = profile.get("fields_to_ask", None)
        if fields_to_ask is None:
            # If fields_to_ask doesn't exist, initialize it with all required fields
            fields_to_ask = [field for field in self.required_fields if not profile.get(field)]
            # Update profile with initial fields_to_ask
            db.update_user_profile(
                user_id=self.user_id,
                data={
                    "fields_to_ask": fields_to_ask,
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
        return fields_to_ask
        
    async def handle_onboarding(self, message_text: str, profile: Dict[str, Any]) -> str:
        """Handle onboarding flow dynamically based on fields_to_ask."""
        try:
            language = profile.get("language", "en")
            fields_to_ask = self.initialize_fields_to_ask(profile)
            
            if not fields_to_ask:
                # All required data collected, generate summary
                return await self.generate_profile_summary(profile)
                
            current_field = fields_to_ask[0]
            
            # Try to store the current answer
            stored = await self.store_profile_data(
                current_field,
                message_text,
                profile
            )
            
            if not stored:
                # If storage failed, ask for the same field again with retry flag
                return await self.generate_field_question(
                    current_field,
                    language,
                    True  # Indicate this is a retry
                )
            
            # Get updated profile after storage
            updated_profile = db.get_user_profile(self.user_id)
            if not updated_profile:
                raise ValueError("User profile not found after update")
                
            # Remove the field we just stored from fields_to_ask
            fields_to_ask = updated_profile.get("fields_to_ask", [])
            if current_field in fields_to_ask:
                fields_to_ask.remove(current_field)
                
            # Update fields_to_ask in profile
            db.update_user_profile(
                user_id=self.user_id,
                data={
                    "fields_to_ask": fields_to_ask,
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            if not fields_to_ask:
                # All data collected, generate summary
                return await self.generate_profile_summary(updated_profile)
                
            # Generate question for the next field
            return await self.generate_field_question(fields_to_ask[0], language)
            
        except Exception as e:
            logger.error(f"Error in onboarding: {e}", exc_info=True)
            return await self.get_error_message(profile.get("language", "en"))
            
    async def store_profile_data(
        self,
        field: str,
        value: str,
        profile: Dict[str, Any]
    ) -> bool:
        """Store profile data with validation."""
        try:
            # Create system prompt for data validation
            system_prompt = f"""You are a data validation expert. Analyze the user's input for the field '{field}'.
Return a JSON object with:
- valid: boolean
- value: processed value (converted to appropriate type)
- error: error message if invalid, null if valid

The response should be in the user's language ({profile.get('language', 'en')})."""
            
            # Create validation prompt based on field
            validation_prompt = self.get_validation_prompt(field, value, profile)
            
            # Get validation result from LLM
            response = await deepseek.chat_completion(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": validation_prompt}],
                temperature=0.1
            )
            
            try:
                result = json.loads(response.strip())
                if not result.get("valid", False):
                    return False
                    
                # Update profile with validated data
                success = db.update_user_profile(
                    user_id=self.user_id,
                    data={
                        field: result["value"],
                        "updated_at": datetime.utcnow().isoformat()
                    }
                )
                return success
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response from LLM: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error storing profile data: {e}")
            return False
            
    def get_validation_prompt(self, field: str, value: str, profile: Dict[str, Any]) -> str:
        """Get validation prompt based on field type."""
        prompts = {
            "first_name": f"""Validate name: "{value}"
Rules:
- Must be a real name
- No numbers or special characters
- Length between 2-50 characters
- Accept names in any language/script""",
            
            "age": f"""Validate age: "{value}"
Rules:
- Must be a number between 13-100
- Convert text numbers to integers
- Handle numbers written in any language""",
            
            "height_cm": f"""Validate height: "{value}"
Rules:
- Must be between 100-250 cm
- Convert to float
- Remove 'cm' or any other height unit if present
- Handle numbers written in any language""",
            
            "current_weight": f"""Validate weight: "{value}"
Rules:
- Must be between 30-300 kg
- Convert to float
- Remove 'kg' or any other weight unit if present
- Handle numbers written in any language""",
            
            "target_weight": f"""Validate target weight: "{value}"
Context: Current weight is {profile.get('current_weight', 0)}kg
Rules:
- Must be between 30-300 kg
- Must be within 50kg of current weight
- Convert to float
- Remove 'kg' or any other weight unit if present
- Handle numbers written in any language""",
            
            "activity_level": f"""Validate activity level: "{value}"
Rules:
- Must match one: sedentary, light, moderate, very_active, extra_active
- Convert similar terms to these categories
- Handle descriptions in any language""",
            
            "diet_restrictions": f"""Validate diet restrictions: "{value}"
Rules:
- Convert to list of valid restrictions
- Valid options: vegetarian, vegan, halal, kosher, gluten_free, dairy_free, nut_free
- Multiple can be specified
- Handle descriptions in any language""",
            
            "health_conditions": f"""Validate health conditions: "{value}"
Rules:
- Convert to list of valid conditions
- Valid options: diabetes, hypertension, heart_disease, celiac, none
- Multiple can be specified
- Handle descriptions in any language"""
        }
        
        return prompts.get(field, f"Validate {field}: {value}")
        
    async def generate_field_question(
        self,
        field: str,
        language: str,
        is_retry: bool = False
    ) -> str:
        """Generate a natural question for the required field."""
        try:
            # Create prompt for question generation
            prompt = f"""Generate a friendly question in {language} to ask for the user's {field.replace('_', ' ')}.

Guidelines:
- Be conversational and friendly
- Include any relevant examples or hints
- If this is a retry ({is_retry}), be more helpful and specific
- Use appropriate emojis
- Keep it concise

Field: {field}
Is retry: {is_retry}"""
            
            response = await deepseek.chat_completion(
                system_prompt="You are a friendly and supportive diet coach.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating question: {e}")
            return await self.get_error_message(language)
            
    async def generate_profile_summary(self, profile: Dict[str, Any]) -> str:
        """Generate a summary of the user's profile and goals."""
        try:
            language = profile.get("language", "en")
            
            # Create prompt for summary generation
            prompt = f"""Generate a friendly summary in {language} for a user with these details:
{json.dumps(profile, indent=2)}

The summary should:
1. Thank them for providing their information
2. Acknowledge their specific goals and restrictions
3. Offer encouragement
4. Explain how you'll help them achieve their goals
5. Invite them to start their journey

Keep it concise, warm, and use appropriate emojis."""
            
            response = await deepseek.chat_completion(
                system_prompt="You are a supportive and knowledgeable diet coach.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            # Update state to regular chat
            db.update_user_profile(
                user_id=self.user_id,
                data={
                    "conversation_state": "chat",
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return await self.get_error_message(language)
            
    async def get_error_message(self, language: str) -> str:
        """Get a localized error message."""
        prompt = f"""Generate a friendly error message in {language}.
The message should:
1. Apologize for the error
2. Ask them to try again
3. Be encouraging

Keep it concise and use appropriate emojis."""
        
        try:
            response = await deepseek.chat_completion(
                system_prompt="You are a friendly and supportive diet coach.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return response.strip()
        except:
            # Fallback error messages
            messages = {
                "en": "I apologize, but I encountered an error. Please try again. 🙏",
                "fr": "Je suis désolé, mais j'ai rencontré une erreur. Veuillez réessayer. 🙏",
                "es": "Lo siento, pero encontré un error. Por favor, inténtelo de nuevo. 🙏",
                "ar": "عذراً، لقد واجهت خطأ. يرجى المحاولة مرة أخرى. 🙏"
            }
            return messages.get(language, messages["en"])
            
    async def handle_chat(self, message_text: str, profile: Dict[str, Any]) -> str:
        """Handle regular chat interaction."""
        # Regular chat handling implementation here
        pass 