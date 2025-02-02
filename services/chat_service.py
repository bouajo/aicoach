"""
Service for handling chat interactions and user profile management.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from services.deepseek_service import deepseek
from agents.diet_agent import DietAgent
from data.database import db

logger = logging.getLogger(__name__)

# Language-specific messages
MESSAGES = {
    "language_confirmed": {
        "en": "👍 Great! I'll communicate with you in English. Let's start by getting to know you better. What's your name?",
        "ar": "👍 رائع! سأتواصل معك باللغة العربية. دعنا نبدأ بالتعرف عليك بشكل أفضل. ما اسمك؟",
        "es": "👍 ¡Excelente! Me comunicaré contigo en español. Empecemos conociéndote mejor. ¿Cómo te llamas?",
        "fr": "👍 Parfait! Je communiquerai avec vous en français. Commençons par faire connaissance. Comment vous appelez-vous?"
    },
    "invalid_language": {
        "en": "❌ I'm sorry, I didn't understand your language preference. Please try again with one of the supported languages: English, Arabic, Spanish, or French.",
        "ar": "❌ عذراً، لم أفهم تفضيلك للغة. يرجى المحاولة مرة أخرى باستخدام إحدى اللغات المدعومة: الإنجليزية أو العربية أو الإسبانية أو الفرنسية.",
        "es": "❌ Lo siento, no entendí tu preferencia de idioma. Por favor, intenta de nuevo con uno de los idiomas admitidos: inglés, árabe, español o francés.",
        "fr": "❌ Désolé, je n'ai pas compris votre préférence linguistique. Veuillez réessayer avec l'une des langues prises en charge : anglais, arabe, espagnol ou français."
    }
}

# Language detection prompt
LANGUAGE_DETECTION_PROMPT = """
Analyze the following user input and determine which language they want to use.
Valid languages are: English (en), Arabic (ar), Spanish (es), French (fr)

Input: {input_text}

Return only the two-letter language code (en/ar/es/fr) that best matches their intent.
If the input doesn't clearly indicate a language preference, return 'en'.

Examples:
- "I want English" -> "en"
- "Arabic please" -> "ar"
- "🇫🇷" -> "fr"
- "español" -> "es"
- "french" -> "fr"
- "العربية" -> "ar"
- "hi" -> "en"
"""

class ChatService:
    """Service for handling chat interactions."""
    
    def __init__(self):
        self.agents: Dict[str, DietAgent] = {}
        
    def get_agent(self, user_id: str) -> DietAgent:
        """Get or create an agent for a user."""
        if user_id not in self.agents:
            self.agents[user_id] = DietAgent(user_id)
        return self.agents[user_id]
        
    async def detect_language_preference(self, input_text: str) -> str:
        """Detect language preference from user input using LLM."""
        try:
            # Format the prompt with user input
            prompt = LANGUAGE_DETECTION_PROMPT.format(input_text=input_text)
            
            # Get language code from LLM
            response = await deepseek.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1  # Low temperature for consistent results
            )
            
            # Extract and validate language code
            lang_code = response.strip().lower()
            if lang_code in ["en", "ar", "es", "fr"]:
                return lang_code
                
            logger.warning(f"Invalid language code from LLM: {lang_code}, defaulting to 'en'")
            return "en"
            
        except Exception as e:
            logger.error(f"Error detecting language: {e}", exc_info=True)
            return "en"  # Default to English on error
        
    async def process_message(
        self,
        user_id: str,
        message_text: str,
        message_id: str,
        phone_number: str
    ) -> Optional[str]:
        """
        Process an incoming message.
        
        Args:
            user_id: The user's UUID
            message_text: The message content
            message_id: The message ID from WhatsApp
            phone_number: The user's phone number
            
        Returns:
            Optional[str]: The response message if any
        """
        try:
            # Get user profile
            profile = db.get_user_profile(user_id)
            if not profile:
                logger.error(f"No profile found for user {user_id}")
                return None
                
            # Handle language selection first
            if profile.get("conversation_state") == "language_selection":
                # Use webhook service's language detection
                from services.webhook_service import webhook_service
                detected_lang = await webhook_service.detect_language_preference(message_text)
                return await self.handle_language_selection(user_id, detected_lang, profile)
                
            # Use diet agent for all other interactions
            agent = self.get_agent(user_id)
            response = await agent.process_message(message_text, phone_number)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return "I apologize, but I encountered an error. Please try again."
            
    async def handle_language_selection(
        self,
        user_id: str,
        detected_lang: str,
        profile: Dict[str, Any]
    ) -> str:
        """Handle language selection for new users."""
        try:
            # Map language codes to names and RTL settings
            language_map = {
                "en": ("English", False),
                "ar": ("العربية", True),
                "es": ("Español", False),
                "fr": ("Français", False)
            }
            
            language_name, is_rtl = language_map[detected_lang]
            
            # Update user profile with selected language
            success = db.update_user_profile(
                user_id=user_id,
                data={
                    "language": detected_lang,
                    "language_name": language_name,
                    "is_rtl": is_rtl,
                    "conversation_state": "onboarding",
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            if not success:
                raise Exception("Failed to update user profile")
            
            # Return confirmation in selected language
            return MESSAGES["language_confirmed"][detected_lang]
            
        except Exception as e:
            logger.error(f"Error handling language selection: {e}", exc_info=True)
            # Return error in current language or English
            current_lang = profile.get("language", "en")
            return MESSAGES["invalid_language"][current_lang]

    def _maybe_update_summary(self, user_id: str) -> None:
        """Update conversation summary if needed."""
        try:
            # Get recent messages
            messages = db.get_recent_messages(user_id, limit=10)
            if not messages:
                return
                
            # Extract text for summarization
            text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
            
            # Generate summary
            summary = deepseek.summarize_text(text)
            
            # Update user context
            db.update_user_context(user_id, {
                "summary": summary,
                "updated_at": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error updating summary: {e}")

    async def handle_onboarding(self, user_id: str, message_text: str, language: str) -> str:
        """Handle the onboarding process to collect user data.
        
        Args:
            user_id: The user's ID
            message_text: The user's message
            language: The user's preferred language
            
        Returns:
            str: The response message
        """
        try:
            # Get user profile
            profile = db.get_user_profile(user_id)
            if not profile:
                raise ValueError("User profile not found")
            
            # Get current onboarding data
            first_name = profile.get("first_name")
            age = profile.get("age")
            height_cm = profile.get("height_cm")
            current_weight = profile.get("current_weight")
            target_weight = profile.get("target_weight")
            
            # Determine next step based on missing data
            if not first_name:
                # Store name
                success = db.update_user_profile(
                    user_id=user_id,
                    data={
                        "first_name": message_text,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                )
                if not success:
                    raise Exception("Failed to store name")
                return self.get_localized_message("ask_age", language)
                
            elif not age:
                try:
                    age_value = int(message_text.strip())
                    if age_value < 13 or age_value > 100:
                        return self.get_localized_message("invalid_age", language)
                    
                    success = db.update_user_profile(
                        user_id=user_id,
                        data={
                            "age": age_value,
                            "updated_at": datetime.utcnow().isoformat()
                        }
                    )
                    if not success:
                        raise Exception("Failed to store age")
                    return self.get_localized_message("ask_height", language)
                except ValueError:
                    return self.get_localized_message("invalid_age", language)
                    
            elif not height_cm:
                try:
                    # Remove 'cm' if present and convert to float
                    height = float(message_text.lower().replace("cm", "").strip())
                    if height < 100 or height > 250:
                        return self.get_localized_message("invalid_height", language)
                    
                    success = db.update_user_profile(
                        user_id=user_id,
                        data={
                            "height_cm": height,
                            "updated_at": datetime.utcnow().isoformat()
                        }
                    )
                    if not success:
                        raise Exception("Failed to store height")
                    return self.get_localized_message("ask_weight", language)
                except ValueError:
                    return self.get_localized_message("invalid_height", language)
                    
            elif not current_weight:
                try:
                    # Remove 'kg' if present and convert to float
                    weight = float(message_text.lower().replace("kg", "").strip())
                    if weight < 30 or weight > 300:
                        return self.get_localized_message("invalid_weight", language)
                    
                    success = db.update_user_profile(
                        user_id=user_id,
                        data={
                            "current_weight": weight,
                            "start_weight": weight,  # Also set as start weight
                            "updated_at": datetime.utcnow().isoformat()
                        }
                    )
                    if not success:
                        raise Exception("Failed to store weight")
                    return self.get_localized_message("ask_target", language)
                except ValueError:
                    return self.get_localized_message("invalid_weight", language)
                    
            elif not target_weight:
                try:
                    # Remove 'kg' if present and convert to float
                    target = float(message_text.lower().replace("kg", "").strip())
                    if abs(target - current_weight) > 50 or target < 30 or target > 300:
                        return self.get_localized_message("invalid_target", language)
                    
                    success = db.update_user_profile(
                        user_id=user_id,
                        data={
                            "target_weight": target,
                            "conversation_state": "chat",  # Move to regular chat state
                            "updated_at": datetime.utcnow().isoformat()
                        }
                    )
                    if not success:
                        raise Exception("Failed to store target weight")
                    
                    # Generate summary message
                    return await self.generate_onboarding_summary(user_id, language)
                except ValueError:
                    return self.get_localized_message("invalid_target", language)
            
            else:
                # All data collected, move to chat state
                return await self.process_message(user_id, message_text)
                
        except Exception as e:
            return self.get_localized_message("error", language)
            
    def get_localized_message(self, key: str, language: str) -> str:
        """Get a localized message."""
        messages = {
            "ask_age": {
                "en": "Thanks! Now, how old are you? (Please enter a number between 13-100)",
                "fr": "Merci ! Quel âge avez-vous ? (Veuillez entrer un nombre entre 13-100)",
                "es": "¡Gracias! ¿Qué edad tienes? (Por favor, ingresa un número entre 13-100)",
                "ar": "شكراً! كم عمرك؟ (يرجى إدخال رقم بين 13-100)"
            },
            "invalid_age": {
                "en": "Please enter a valid age between 13 and 100 years.",
                "fr": "Veuillez entrer un âge valide entre 13 et 100 ans.",
                "es": "Por favor, ingresa una edad válida entre 13 y 100 años.",
                "ar": "يرجى إدخال عمر صالح بين 13 و 100 سنة."
            },
            "ask_height": {
                "en": "What's your height in centimeters? (e.g., 175)",
                "fr": "Quelle est votre taille en centimètres ? (ex: 175)",
                "es": "¿Cuál es tu altura en centímetros? (ej: 175)",
                "ar": "ما هو طولك بالسنتيمتر؟ (مثال: 175)"
            },
            "invalid_height": {
                "en": "Please enter a valid height between 100 and 250 cm.",
                "fr": "Veuillez entrer une taille valide entre 100 et 250 cm.",
                "es": "Por favor, ingresa una altura válida entre 100 y 250 cm.",
                "ar": "يرجى إدخال طول صالح بين 100 و 250 سم."
            },
            "ask_weight": {
                "en": "What's your current weight in kilograms? (e.g., 70)",
                "fr": "Quel est votre poids actuel en kilogrammes ? (ex: 70)",
                "es": "¿Cuál es tu peso actual en kilogramos? (ej: 70)",
                "ar": "ما هو وزنك الحالي بالكيلوغرام؟ (مثال: 70)"
            },
            "invalid_weight": {
                "en": "Please enter a valid weight between 30 and 300 kg.",
                "fr": "Veuillez entrer un poids valide entre 30 et 300 kg.",
                "es": "Por favor, ingresa un peso válido entre 30 y 300 kg.",
                "ar": "يرجى إدخال وزن صالح بين 30 و 300 كغ."
            },
            "ask_target": {
                "en": "What's your target weight in kilograms? (e.g., 65)",
                "fr": "Quel est votre poids cible en kilogrammes ? (ex: 65)",
                "es": "¿Cuál es tu peso objetivo en kilogramos? (ej: 65)",
                "ar": "ما هو وزنك المستهدف بالكيلوغرام؟ (مثال: 65)"
            },
            "invalid_target": {
                "en": "Please enter a realistic target weight (within 50kg of your current weight).",
                "fr": "Veuillez entrer un poids cible réaliste (dans une fourchette de 50kg par rapport à votre poids actuel).",
                "es": "Por favor, ingresa un peso objetivo realista (dentro de 50kg de tu peso actual).",
                "ar": "يرجى إدخال وزن مستهدف واقعي (ضمن 50 كغ من وزنك الحالي)."
            },
            "error": {
                "en": "I apologize, but I encountered an error. Please try again.",
                "fr": "Je suis désolé, mais j'ai rencontré une erreur. Veuillez réessayer.",
                "es": "Lo siento, pero encontré un error. Por favor, inténtelo de nuevo.",
                "ar": "عذراً، لقد واجهت خطأ. يرجى المحاولة مرة أخرى."
            }
        }
        return messages.get(key, {}).get(language, messages[key]["en"])
        
    async def generate_onboarding_summary(self, user_id: str, language: str) -> str:
        """Generate a summary of the user's profile and goals."""
        try:
            profile = db.get_user_profile(user_id)
            if not profile:
                raise ValueError("User profile not found")
                
            # Calculate weight difference
            current_weight = profile.get("current_weight", 0)
            target_weight = profile.get("target_weight", 0)
            weight_diff = abs(target_weight - current_weight)
            goal_type = "lose" if target_weight < current_weight else "gain"
            
            # Create prompt for the summary
            prompt = f"""Generate a friendly and motivational summary in {language} for a user with these details:
Name: {profile.get('first_name')}
Current weight: {current_weight}kg
Target weight: {target_weight}kg
Goal: {goal_type} {weight_diff:.1f}kg
Height: {profile.get('height_cm')}cm
Age: {profile.get('age')}

The message should:
1. Thank them for providing their information
2. Acknowledge their specific goal
3. Offer encouragement
4. Explain how you'll help them
5. Invite them to ask their first question

Keep it concise, warm, and use appropriate emojis."""
            
            response = await deepseek.chat_completion(
                system_prompt="You are a supportive and knowledgeable diet coach.",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            return response.strip()
            
        except Exception as e:
            return self.get_localized_message("error", language)

# Create a single instance
chat_service = ChatService()
