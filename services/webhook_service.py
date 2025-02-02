"""
Service for handling WhatsApp webhook events.
"""

import os
import logging
import json
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from fastapi import APIRouter, Request, Response, HTTPException
from services.whatsapp_service import whatsapp
from utils.uuid_utils import phone_to_uuid
from data.database import db
from services.deepseek_service import deepseek
from services.diet_agent import DietAgent

logger = logging.getLogger(__name__)

# Default welcome message in English
WELCOME_MESSAGE = """👋 Hello! I'm Eric, your personal diet coach.

I've helped thousands of people achieve their health and wellness goals over the past 20 years. I'm here to understand your unique journey, create a personalized plan, and support you every step of the way.

Before we begin our journey together, I want to make sure we communicate in the language you're most comfortable with.

You can choose your language by:
• Simply writing a message in your preferred language
• Using a flag emoji (🇬🇧 🇦🇪 🇪🇸 🇫🇷)
• Or typing the language name

Feel free to express yourself naturally - I'll understand! 😊"""

# System prompt for language detection
LANGUAGE_DETECTION_SYSTEM_PROMPT = """You are a language detection expert. Your task is to analyze user input and determine their preferred language.
You must respond with a JSON object containing:
1. The ISO 639-1 two-letter language code
2. The language name in English
3. Whether the language is written right-to-left (RTL)

Be flexible in understanding both direct language requests and implicit language usage.
Support ANY language the user might want to use."""

# Language detection prompt
LANGUAGE_DETECTION_PROMPT = """Analyze this text to determine the user's preferred language.

User message: "{text}"

Respond with a JSON object in this exact format:
{{
    "language_code": "two-letter-code",
    "language_name": "Language Name in English",
    "is_rtl": boolean-true-or-false
}}

Examples of responses:
- Hebrew: {{"language_code": "he", "language_name": "Hebrew", "is_rtl": true}}
- Japanese: {{"language_code": "ja", "language_name": "Japanese", "is_rtl": false}}
- Russian: {{"language_code": "ru", "language_name": "Russian", "is_rtl": false}}
- Hindi: {{"language_code": "hi", "language_name": "Hindi", "is_rtl": false}}
- Arabic: {{"language_code": "ar", "language_name": "Arabic", "is_rtl": true}}
- French: {{"language_code": "fr", "language_name": "French", "is_rtl": false}}
- Chinese: {{"language_code": "zh", "language_name": "Chinese", "is_rtl": false}}
- Korean: {{"language_code": "ko", "language_name": "Korean", "is_rtl": false}}

Handle ANY language, not just these examples. If you're unsure about the RTL status, set it to false.
Respond only with the JSON object, no other text."""

class WebhookService:
    """Service for handling WhatsApp webhooks."""
    
    def __init__(self):
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN")
        if not self.verify_token:
            raise ValueError("WHATSAPP_VERIFY_TOKEN is required")
            
        self.router = APIRouter()
        self._setup_routes()
        self.agents: Dict[str, DietAgent] = {}
        
    def get_agent(self, user_id: str) -> DietAgent:
        """Get or create an agent for a user."""
        if user_id not in self.agents:
            self.agents[user_id] = DietAgent(user_id)
        return self.agents[user_id]
        
    async def detect_language_preference(self, input_text: str) -> Tuple[str, str, bool]:
        """
        Detect language preference from user input using LLM.
        
        Args:
            input_text: The user's input text to analyze
            
        Returns:
            Tuple[str, str, bool]: (language_code, language_name, is_rtl)
        """
        try:
            # Format the prompt with user input
            prompt = LANGUAGE_DETECTION_PROMPT.format(text=input_text)
            
            # Get language info from LLM with system prompt
            response = await deepseek.chat_completion(
                system_prompt=LANGUAGE_DETECTION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1  # Low temperature for consistent results
            )
            
            try:
                # Clean the response - remove any non-JSON text
                response_text = response.strip()
                # Find the first '{' and last '}'
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    response_text = response_text[start:end]
                
                # Parse the JSON response
                lang_info = json.loads(response_text)
                
                # Extract and validate the language information
                lang_code = lang_info.get("language_code", "").lower()
                lang_name = lang_info.get("language_name", "")
                is_rtl = bool(lang_info.get("is_rtl", False))
                
                if not lang_code or not lang_name:
                    raise ValueError("Invalid language information")
                
                logger.info(f"Detected language: {lang_name} ({lang_code}), RTL: {is_rtl}")
                return lang_code, lang_name, is_rtl
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Error parsing language detection response: {e}")
                logger.error(f"Raw response: {response}")
                return "en", "English", False
                
        except Exception as e:
            logger.error(f"Error detecting language: {e}", exc_info=True)
            return "en", "English", False  # Default to English on error
            
    def store_conversation_message(
        self,
        user_id: str,
        role: str,
        content: str
    ) -> None:
        """Store a message in the conversation history."""
        try:
            # Store the message
            success = db.store_message(
                user_id=user_id,
                role=role,
                content=content
            )
            
            if not success:
                logger.error("Failed to store message")
                return
                
            # Get message count
            message_count = db.get_message_count(user_id)
            
            # Update summary every 10 messages
            if message_count % 10 == 0:
                agent = self.get_agent(user_id)
                agent._maybe_update_summary()
                
        except Exception as e:
            logger.error(f"Error storing message: {e}", exc_info=True)
            
    async def send_message_with_retry(self, phone_number: str, message: str, max_retries: int = 3) -> bool:
        """Send a WhatsApp message with retry logic and token refresh.
        
        Args:
            phone_number: The recipient's phone number
            message: The message to send
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        for attempt in range(max_retries):
            try:
                await whatsapp.send_message(phone_number, message)
                return True
            except HTTPException as e:
                if "token" in str(e).lower() and attempt < max_retries - 1:
                    logger.warning(f"Token error on attempt {attempt + 1}, trying to refresh token")
                    try:
                        await whatsapp.refresh_token()
                        continue
                    except Exception as refresh_error:
                        logger.error(f"Token refresh failed: {refresh_error}")
                elif attempt < max_retries - 1:
                    logger.warning(f"Message send failed on attempt {attempt + 1}, retrying...")
                    continue
                else:
                    logger.error(f"Failed to send message after {max_retries} attempts")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error sending message: {e}")
                if attempt < max_retries - 1:
                    continue
                return False
        return False
        
    async def handle_new_user(self, phone_number: str) -> Dict[str, Any]:
        """Handle a new user's first interaction."""
        try:
            # Create basic profile first
            user_id = phone_to_uuid(phone_number)
            
            # Create profile with initial fields to ask
            success = db.update_user_profile(
                user_id=user_id,
                data={
                    "phone_number": phone_number,
                    "conversation_state": "language_selection",
                    "language": "en",
                    "language_name": "English",
                    "is_rtl": False,
                    "fields_to_ask": [
                        "first_name",
                        "age",
                        "height_cm",
                        "current_weight",
                        "target_weight",
                        "activity_level",
                        "diet_restrictions",
                        "health_conditions"
                    ],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            if not success:
                raise Exception("Failed to create user profile")
                
            # Try to send welcome message
            if not await self.send_message_with_retry(phone_number, WELCOME_MESSAGE):
                # If message fails but profile was created, return success but log the error
                logger.error("Failed to send welcome message to new user")
                return {
                    "status": "partial_success",
                    "message": "User profile created but welcome message failed"
                }
                
            # Store the welcome message only if it was sent
            self.store_conversation_message(
                user_id=user_id,
                role="assistant",
                content=WELCOME_MESSAGE
            )
            
            return {
                "status": "success",
                "message": "New user created and welcome message sent"
            }
            
        except Exception as e:
            logger.error(f"Error handling new user: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e)
            }
            
    async def handle_webhook(self, request: Request) -> Dict[str, Any]:
        """Handle incoming webhook events from WhatsApp."""
        try:
            data = await request.json()
            logger.debug(f"Received webhook data: {json.dumps(data, indent=2)}")
            
            # Handle verification requests first
            if "challenge" in data:
                challenge = data["challenge"]
                return Response(content=challenge, media_type="text/plain")
                
            # Extract message details
            entry = data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            
            if "messages" not in value:
                return {"status": "success", "message": "Non-message webhook received"}
                
            message = value["messages"][0]
            contact = value.get("contacts", [{}])[0]
            
            # Extract user info
            phone_number = contact.get("wa_id")
            if not phone_number:
                return {"status": "error", "message": "No phone number found"}
                
            # Generate deterministic UUID from phone number
            user_id = phone_to_uuid(phone_number)
            
            # Extract message content
            message_type = message.get("type", "")
            if message_type != "text":
                return {"status": "error", "message": "Unsupported message type"}
                
            text = message.get("text", {}).get("body", "").strip()
            if not text:
                return {"status": "error", "message": "Empty message"}
                
            # Log the incoming message
            logger.info(f"Processing message from {user_id} (phone: {phone_number}): {text}")
            
            try:
                # Check if user exists
                user_profile = db.get_user_profile(user_id)
                
                if not user_profile:
                    # Handle new user first - only send welcome message
                    result = await self.handle_new_user(phone_number)
                    if result["status"] == "error":
                        raise Exception(result["message"])
                    return result
                
                # Store the user message
                self.store_conversation_message(
                    user_id=user_id,
                    role="user",
                    content=text
                )

                response = None
                
                # Get current state
                state = user_profile.get("conversation_state", "language_selection")
                
                if state == "language_selection":
                    # Handle language selection
                    response = await self.handle_language_selection(user_id, phone_number, text)
                    if not response:
                        raise Exception("Failed to handle language selection")
                    
                else:
                    # All other states handled by diet agent
                    agent = self.get_agent(user_id)
                    response = await agent.process_message(text, phone_number)
                    if response:
                        if await self.send_message_with_retry(phone_number, response):
                            self.store_conversation_message(
                                user_id=user_id,
                                role="assistant",
                                content=response
                            )
                
                return {
                    "status": "success",
                    "message": "Message processed successfully",
                    "response": response
                }
                
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                # Get error message from agent
                agent = self.get_agent(user_id)
                error_message = await agent.get_error_message(user_profile.get("language", "en"))
                
                # Try to send error message
                try:
                    if await self.send_message_with_retry(phone_number, error_message):
                        self.store_conversation_message(
                            user_id=user_id,
                            role="assistant",
                            content=error_message
                        )
                except:
                    logger.error("Failed to send error message", exc_info=True)
                    
                return {
                    "status": "error",
                    "message": "Error processing message",
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

    def get_localized_message(self, key: str, language: str) -> str:
        """Get a localized message for a specific key and language."""
        messages = {
            "language_confirmed": {
                "en": "👍 Great! I'll communicate with you in English. Let's start by getting to know you better.",
                "fr": "👍 Parfait ! Je communiquerai avec vous en français. Commençons par faire connaissance.",
                "es": "👍 ¡Excelente! Me comunicaré contigo en español. Empecemos conociéndote mejor.",
                "ar": "👍 رائع! سأتواصل معك باللغة العربية. دعنا نبدأ بالتعرف عليك بشكل أفضل.",
                "he": "👍 מעולה! אני אתקשר איתך בעברית. בוא נתחיל להכיר אותך טוב יותר.",
                "ru": "👍 Отлично! Я буду общаться с вами на русском. Давайте начнем знакомство.",
                "hi": "👍 बहुत अच्छा! मैं आपसे हिंदी में बात करूंगा। आइए आपको बेहतर जानने की शुरुआत करें।",
                "ja": "👍 素晴らしい！日本語でコミュニケーションを取らせていただきます。まずはあなたのことを知っていきましょう。",
                "ko": "👍 좋습니다! 한국어로 대화하겠습니다. 먼저 당신에 대해 알아가 보겠습니다.",
                "zh": "👍 太好了！我将用中文与您交流。让我们开始更好地了解您。"
            },
            "ask_name": {
                "en": "What's your name? 😊",
                "fr": "Comment vous appelez-vous ? 😊",
                "es": "¿Cómo te llamas? 😊",
                "ar": "ما اسمك؟ 😊",
                "he": "מה שמך? 😊",
                "ru": "Как вас зовут? 😊",
                "hi": "आपका नाम क्या है? 😊",
                "ja": "お名前を教えていただけますか？😊",
                "ko": "이름이 무엇인가요? 😊",
                "zh": "您叫什么名字？😊"
            },
            "error": {
                "en": "I apologize, but I encountered an error. Please try again. 🙏",
                "fr": "Je suis désolé, mais j'ai rencontré une erreur. Veuillez réessayer. 🙏",
                "es": "Lo siento, pero encontré un error. Por favor, inténtelo de nuevo. 🙏",
                "ar": "عذراً، لقد واجهت خطأ. يرجى المحاولة مرة أخرى. 🙏",
                "he": "אני מתנצל, אבל נתקלתי בשגיאה. אנא נסה שוב. 🙏",
                "ru": "Приношу извинения, но произошла ошибка. Пожалуйста, попробуйте еще раз. 🙏",
                "hi": "मैं क्षमा चाहता हूं, लेकिन एक त्रुटि हुई। कृपया पुनः प्रयास करें। 🙏",
                "ja": "申し訳ありませんが、エラーが発生しました。もう一度お試しください。🙏",
                "ko": "죄송합니다만, 오류가 발생했습니다. 다시 시도해 주세요. 🙏",
                "zh": "抱歉，我遇到了错误。请重试。🙏"
            }
        }
        
        # Get messages for the requested key, defaulting to error messages if key not found
        message_group = messages.get(key, messages["error"])
        # Get message in requested language, defaulting to English if language not found
        return message_group.get(language, message_group["en"])

    async def handle_language_selection(self, user_id: str, phone_number: str, text: str) -> Optional[str]:
        """Handle language selection and transition to onboarding."""
        try:
            # Detect language
            lang_code, lang_name, is_rtl = await self.detect_language_preference(text)
            
            # Update user profile with detected language and move to onboarding
            success = db.update_user_profile(
                user_id=user_id,
                data={
                    "language": lang_code,
                    "language_name": lang_name,
                    "is_rtl": is_rtl,
                    "conversation_state": "onboarding",
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            if not success:
                raise Exception("Failed to update user language preference")
            
            # Send confirmation message in the selected language
            confirmation = self.get_localized_message("language_confirmed", lang_code)
            name_question = self.get_localized_message("ask_name", lang_code)
            response = f"{confirmation}\n\n{name_question}"
            
            if await self.send_message_with_retry(phone_number, response):
                self.store_conversation_message(
                    user_id=user_id,
                    role="assistant",
                    content=response
                )
                return response
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling language selection: {e}", exc_info=True)
            return None

    def _setup_routes(self):
        @self.router.get("/webhook")
        async def verify_webhook(request: Request):
            """Verify webhook endpoint for WhatsApp API."""
            try:
                # Get query parameters
                params = dict(request.query_params)
                logger.info(f"Webhook verification request params: {params}")
                
                # Extract verification parameters
                mode = params.get("hub.mode")
                token = params.get("hub.verify_token")
                challenge = params.get("hub.challenge")
                
                # Verify token
                if mode == "subscribe" and token == self.verify_token:
                    if not challenge:
                        raise ValueError("Missing hub.challenge")
                    logger.info("Webhook verified successfully")
                    return Response(content=challenge, media_type="text/plain")
                    
                raise ValueError("Invalid verification token")
                
            except ValueError as e:
                logger.error(f"Invalid challenge format: {e}")
                raise HTTPException(status_code=400, detail=str(e))
                
            except Exception as e:
                logger.error(f"Webhook verification failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
                
        @self.router.post("/webhook")
        async def handle_webhook(request: Request) -> Dict[str, Any]:
            return await self.handle_webhook(request)

# Create a single instance
webhook_service = WebhookService()
# Export the router
router = webhook_service.router