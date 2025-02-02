"""
Diet Coach AI Agent implementation.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json
import os
from .base_agent import BaseAgent
from services.deepseek_service import deepseek

# Load language settings from environment
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
SUPPORTED_LANGUAGES = json.loads(os.getenv("SUPPORTED_LANGUAGES", '["en"]'))

class DietAgent(BaseAgent):
    """AI Diet Coach agent implementation."""
    
    def __init__(self, user_id: str):
        super().__init__(user_id)
        
    def build_system_prompt(self) -> str:
        """Build the system prompt for the diet agent."""
        return """You are Eric 2.0, an AI Diet Coach powered by advanced AI technology. Your role is to:

1. Help users achieve their health and fitness goals through personalized nutrition advice
2. Track their progress and provide motivational support
3. Offer meal planning and recipe suggestions
4. Answer questions about nutrition and healthy eating
5. Maintain a friendly, professional, and encouraging tone

Key Behaviors:
- Always be supportive and non-judgmental
- Provide evidence-based advice
- Personalize responses based on user's goals and preferences
- Encourage sustainable lifestyle changes over quick fixes
- Ask clarifying questions when needed
- Keep track of user's progress and reference it in conversations
- Use emojis appropriately to maintain a friendly tone 🥗 💪 

Safety Guidelines:
- Never provide medical advice
- Recommend consulting healthcare professionals for medical concerns
- Avoid promoting extreme diets or unsafe practices
- Be mindful of eating disorders and refer to professionals when concerned

Remember to:
- Adapt your communication style to the user's preferences
- Keep responses concise but informative
- Celebrate user's successes, no matter how small
- Provide practical, actionable advice
- Stay within your role as a diet coach"""

    async def process_message(self, message_text: str, phone_number: Optional[str] = None) -> str:
        """Process a message from the user.
        
        Args:
            message_text: The text message from the user
            phone_number: Optional phone number of the user
            
        Returns:
            str: The response message to send back to the user
        """
        try:
            # Get user profile
            profile = self.get_user_profile()
            if not profile:
                raise ValueError("User profile not found")
                
            # Get user's language
            language = profile.get("language", "en")
            
            # Get conversation state
            state = profile.get("conversation_state", "init")
            
            # Process message based on state
            if state == "onboarding":
                return await self._handle_onboarding(message_text, profile)
            else:
                return await self._handle_chat(message_text, profile)
                
        except Exception as e:
            logger.error(f"Error in diet agent: {e}", exc_info=True)
            return "I apologize, but I encountered an error. Please try again."
            
    async def _handle_onboarding(self, message_text: str, profile: Dict[str, Any]) -> str:
        """Handle messages during the onboarding process."""
        try:
            # TODO: Implement onboarding flow
            # For now, just move to chat state
            self.update_user_profile({
                "conversation_state": "chat",
                "updated_at": datetime.utcnow().isoformat()
            })
            
            return "Great! I'm here to help you with your diet goals. What would you like to know?"
            
        except Exception as e:
            logger.error(f"Error in onboarding: {e}", exc_info=True)
            return "I apologize, but I encountered an error during onboarding. Please try again."
            
    async def _handle_chat(self, message_text: str, profile: Dict[str, Any]) -> str:
        """Handle regular chat messages."""
        try:
            # Get chat response from LLM
            response = await deepseek.chat_completion(
                system_prompt="You are a helpful diet coach. Provide clear, concise advice.",
                messages=[{"role": "user", "content": message_text}]
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error in chat: {e}", exc_info=True)
            return "I apologize, but I encountered an error. Please try again."

    async def handle_new_user(self, phone_number: str) -> str:
        """Handle a new user's first interaction."""
        # Create initial profile
        await self.update_user_profile({
            "phone_number": phone_number,
            "conversation_state": "language_selection",
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Send welcome message with language selection
        return self.get_language_selection_message()
        
    def get_language_selection_message(self) -> str:
        """Generate the language selection message."""
        messages = {
            "en": "🌍 Welcome! Please select your preferred language:\n",
            "ar": "🌍 مرحباً! الرجاء اختيار لغتك المفضلة:\n",
            "es": "🌍 ¡Bienvenido! Por favor, seleccione su idioma preferido:\n",
            "fr": "🌍 Bienvenue! Veuillez sélectionner votre langue préférée:\n"
        }
        
        # Build language options
        options = {
            "en": "1. English 🇬🇧",
            "ar": "2. العربية 🇦🇪",
            "es": "3. Español 🇪🇸",
            "fr": "4. Français 🇫🇷"
        }
        
        # Combine all supported languages
        message = ""
        for lang in SUPPORTED_LANGUAGES:
            message += messages.get(lang, messages["en"]) + "\n"
        
        # Add options
        for lang in SUPPORTED_LANGUAGES:
            message += options[lang] + "\n"
            
        return message.strip()
        
    async def handle_language_selection(self, message: str, profile: Dict[str, Any]) -> str:
        """Handle language selection."""
        # Map user input to language codes
        language_map = {
            "1": "en", "english": "en", "🇬🇧": "en",
            "2": "ar", "arabic": "ar", "العربية": "ar", "🇦🇪": "ar",
            "3": "es", "spanish": "es", "español": "es", "🇪🇸": "es",
            "4": "fr", "french": "fr", "français": "fr", "🇫🇷": "fr"
        }
        
        selected_lang = language_map.get(message.lower().strip())
        
        if not selected_lang or selected_lang not in SUPPORTED_LANGUAGES:
            return "❌ Please select a valid language option."
            
        # Update profile with selected language
        await self.update_user_profile({
            "language": selected_lang,
            "conversation_state": "onboarding",
            "onboarding_step": "ask_name"
        })
        
        # Return first onboarding message in selected language
        return self.get_localized_message("welcome", selected_lang)
        
    async def handle_onboarding(self, message: str, profile: Dict[str, Any]) -> str:
        """Handle the onboarding process."""
        current_step = profile.get("onboarding_step", "ask_name")
        language = profile.get("language", DEFAULT_LANGUAGE)
        
        # Define onboarding steps and their handlers
        steps = {
            "ask_name": self.handle_name_step,
            "ask_age": self.handle_age_step,
            "ask_height": self.handle_height_step,
            "ask_weight": self.handle_weight_step,
            "ask_target": self.handle_target_step,
            "ask_activity": self.handle_activity_step,
            "ask_diet": self.handle_diet_step,
            "complete": self.complete_onboarding
        }
        
        # Get handler for current step
        handler = steps.get(current_step)
        if not handler:
            return await self.handle_normal_conversation(message, profile)
            
        return await handler(message, profile)
        
    async def handle_name_step(self, message: str, profile: Dict[str, Any]) -> str:
        """Handle name collection step."""
        await self.update_user_profile({
            "first_name": message,
            "onboarding_step": "ask_age"
        })
        
        return self.get_localized_message("ask_age", profile["language"])
        
    async def handle_age_step(self, message: str, profile: Dict[str, Any]) -> str:
        """Handle age collection step."""
        try:
            age = int(message.strip())
            if age < 13 or age > 100:
                return self.get_localized_message("invalid_age", profile["language"])
                
            await self.update_user_profile({
                "age": age,
                "onboarding_step": "ask_height"
            })
            
            return self.get_localized_message("ask_height", profile["language"])
            
        except ValueError:
            return self.get_localized_message("invalid_age", profile["language"])
            
    async def handle_height_step(self, message: str, profile: Dict[str, Any]) -> str:
        """Handle height collection step."""
        try:
            # Remove 'cm' if present and convert to float
            height = float(message.lower().replace("cm", "").strip())
            if height < 100 or height > 250:
                return self.get_localized_message("invalid_height", profile["language"])
                
            await self.update_user_profile({
                "height_cm": height,
                "onboarding_step": "ask_weight"
            })
            
            return self.get_localized_message("ask_weight", profile["language"])
            
        except ValueError:
            return self.get_localized_message("invalid_height", profile["language"])
            
    async def handle_weight_step(self, message: str, profile: Dict[str, Any]) -> str:
        """Handle current weight collection step."""
        try:
            # Remove 'kg' if present and convert to float
            weight = float(message.lower().replace("kg", "").strip())
            if weight < 30 or weight > 300:
                return self.get_localized_message("invalid_weight", profile["language"])
                
            await self.update_user_profile({
                "current_weight": weight,
                "start_weight": weight,  # Also set as start weight
                "onboarding_step": "ask_target"
            })
            
            return self.get_localized_message("ask_target", profile["language"])
            
        except ValueError:
            return self.get_localized_message("invalid_weight", profile["language"])
            
    async def handle_target_step(self, message: str, profile: Dict[str, Any]) -> str:
        """Handle target weight collection step."""
        try:
            # Remove 'kg' if present and convert to float
            target = float(message.lower().replace("kg", "").strip())
            current_weight = profile.get("current_weight", 0)
            
            # Validate target is within reasonable range of current weight
            if abs(target - current_weight) > 50 or target < 30 or target > 300:
                return self.get_localized_message("invalid_target", profile["language"])
                
            await self.update_user_profile({
                "target_weight": target,
                "onboarding_step": "ask_activity"
            })
            
            return self.get_localized_message("ask_activity", profile["language"])
            
        except ValueError:
            return self.get_localized_message("invalid_target", profile["language"])
            
    async def handle_activity_step(self, message: str, profile: Dict[str, Any]) -> str:
        """Handle activity level collection step."""
        # Map numeric or text input to activity levels
        activity_map = {
            "1": "sedentary",
            "2": "light",
            "3": "moderate",
            "4": "very_active",
            "sedentary": "sedentary",
            "light": "light",
            "moderate": "moderate",
            "very_active": "very_active"
        }
        
        activity = activity_map.get(message.lower().strip())
        if not activity:
            return self.get_localized_message("invalid_activity", profile["language"])
            
        await self.update_user_profile({
            "activity_level": activity,
            "onboarding_step": "ask_diet"
        })
        
        return self.get_localized_message("ask_diet", profile["language"])
        
    async def handle_diet_step(self, message: str, profile: Dict[str, Any]) -> str:
        """Handle dietary restrictions collection step."""
        # Save dietary restrictions
        await self.update_user_profile({
            "dietary_restrictions": message.strip(),
            "onboarding_step": "complete",
            "conversation_state": "chat"  # Move to normal chat state
        })
        
        # Generate personalized completion message
        return await self.generate_completion_message(profile)
        
    async def generate_completion_message(self, profile: Dict[str, Any]) -> str:
        """Generate a personalized completion message."""
        language = profile.get("language", DEFAULT_LANGUAGE)
        name = profile.get("first_name", "")
        current_weight = profile.get("current_weight")
        target_weight = profile.get("target_weight")
        
        # Calculate weight difference
        weight_diff = abs(target_weight - current_weight)
        goal_type = "lose" if target_weight < current_weight else "gain"
        
        completion_prompt = f"""
Generate a friendly and motivational onboarding completion message for {name}.
Current weight: {current_weight}kg
Target weight: {target_weight}kg
Goal: {goal_type} {weight_diff:.1f}kg

The message should:
1. Thank them for providing their information
2. Acknowledge their goal
3. Offer encouragement
4. Explain how you'll help them
5. Invite them to ask their first question

Language: {language}
Use appropriate emojis and keep it concise but warm.
"""
        
        try:
            response = await deepseek.chat_completion(
                system_prompt=self.build_system_prompt(),
                messages=[{"role": "user", "content": completion_prompt}],
                temperature=0.7,
                max_tokens=300
            )
            return response
            
        except Exception as e:
            logger.error(f"Error generating completion message: {e}")
            return self.get_localized_message("completion_fallback", language)
            
    def get_localized_message(self, key: str, language: str) -> str:
        """Get a localized message."""
        messages = {
            "welcome": {
                "en": "👋 Welcome! I'm Eric 2.0, your AI Diet Coach. To get started, what's your name?",
                "ar": "👋 مرحباً! أنا إريك 2.0، مدرب التغذية الخاص بك. للبدء، ما اسمك؟",
                "es": "👋 ¡Bienvenido! Soy Eric 2.0, tu entrenador de dieta AI. Para empezar, ¿cómo te llamas?",
                "fr": "👋 Bienvenue! Je suis Eric 2.0, votre coach diététique IA. Pour commencer, quel est votre nom?"
            },
            "ask_age": {
                "en": "Great! How old are you?",
                "ar": "رائع! كم عمرك؟",
                "es": "¡Genial! ¿Cuántos años tienes?",
                "fr": "Super! Quel âge avez-vous?"
            },
            "ask_height": {
                "en": "What's your height in centimeters (cm)?",
                "ar": "ما هو طولك بالسنتيمتر (سم)؟",
                "es": "¿Cuál es tu altura en centímetros (cm)?",
                "fr": "Quelle est votre taille en centimètres (cm)?"
            },
            "ask_weight": {
                "en": "What's your current weight in kilograms (kg)?",
                "ar": "ما هو وزنك الحالي بالكيلوغرام (كغ)؟",
                "es": "¿Cuál es tu peso actual en kilogramos (kg)?",
                "fr": "Quel est votre poids actuel en kilogrammes (kg)?"
            },
            "ask_target": {
                "en": "What's your target weight in kilograms (kg)?",
                "ar": "ما هو وزنك المستهدف بالكيلوغرام (كغ)؟",
                "es": "¿Cuál es tu peso objetivo en kilogramos (kg)?",
                "fr": "Quel est votre poids cible en kilogrammes (kg)?"
            },
            "ask_activity": {
                "en": "How would you describe your activity level?\n1. Sedentary (little or no exercise)\n2. Light (exercise 1-3 times/week)\n3. Moderate (exercise 3-5 times/week)\n4. Very Active (exercise 6-7 times/week)",
                "ar": "كيف تصف مستوى نشاطك؟\n1. خامل (قليل أو لا تمارين)\n2. خفيف (تمارين 1-3 مرات/أسبوع)\n3. معتدل (تمارين 3-5 مرات/أسبوع)\n4. نشط جداً (تمارين 6-7 مرات/أسبوع)",
                "es": "¿Cómo describirías tu nivel de actividad?\n1. Sedentario (poco o ningún ejercicio)\n2. Ligero (ejercicio 1-3 veces/semana)\n3. Moderado (ejercicio 3-5 veces/semana)\n4. Muy Activo (ejercicio 6-7 veces/semana)",
                "fr": "Comment décririez-vous votre niveau d'activité?\n1. Sédentaire (peu ou pas d'exercice)\n2. Léger (exercice 1-3 fois/semaine)\n3. Modéré (exercice 3-5 fois/semaine)\n4. Très Actif (exercice 6-7 fois/semaine)"
            },
            "ask_diet": {
                "en": "Do you have any dietary restrictions or preferences? (e.g., vegetarian, vegan, gluten-free, halal, etc.)",
                "ar": "هل لديك أي قيود أو تفضيلات غذائية؟ (مثل نباتي، نباتي صارم، خالي من الغلوتين، حلال، إلخ)",
                "es": "¿Tienes alguna restricción o preferencia dietética? (p.ej., vegetariano, vegano, sin gluten, halal, etc.)",
                "fr": "Avez-vous des restrictions ou préférences alimentaires? (ex: végétarien, végétalien, sans gluten, halal, etc.)"
            },
            "completion_fallback": {
                "en": "✨ Thank you for providing your information! I'm ready to help you achieve your health and fitness goals. What would you like to know first?",
                "ar": "✨ شكراً لتقديم معلوماتك! أنا مستعد لمساعدتك في تحقيق أهداف صحتك ولياقتك. ماذا تريد أن تعرف أولاً؟",
                "es": "✨ ¡Gracias por proporcionar tu información! Estoy listo para ayudarte a alcanzar tus objetivos de salud y fitness. ¿Qué te gustaría saber primero?",
                "fr": "✨ Merci d'avoir fourni vos informations! Je suis prêt à vous aider à atteindre vos objectifs de santé et de forme. Que souhaitez-vous savoir en premier?"
            }
        }
        
        return messages[key].get(language, messages[key]["en"])
        
    async def handle_normal_conversation(self, message: str, profile: Dict[str, Any]) -> str:
        """Handle normal conversation after onboarding."""
        # Get conversation history and context
        history = await self.get_conversation_history(5)
        context = await self.get_context()
        
        # Build conversation context
        conversation_context = []
        for msg in reversed(history):
            conversation_context.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
        # Add user profile context
        user_context = f"""
User Profile:
- Name: {profile.get('first_name', 'User')}
- Language: {profile.get('language', DEFAULT_LANGUAGE)}
- Current Weight: {profile.get('current_weight')} kg
- Target Weight: {profile.get('target_weight')} kg
- Height: {profile.get('height_cm')} cm
- Age: {profile.get('age')}
- Activity Level: {profile.get('activity_level')}
- Dietary Restrictions: {profile.get('dietary_restrictions')}
"""
        
        # Generate response using LLM
        response = await deepseek.chat_completion(
            system_prompt=self.build_system_prompt() + "\n" + user_context,
            messages=conversation_context + [{"role": "user", "content": message}],
            temperature=0.7,
            max_tokens=500
        )
        
        # Save the interaction
        await self.save_message("user", message)
        await self.save_message("assistant", response)
        
        return response 