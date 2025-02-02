"""
Service for handling chat interactions and user profile management.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from deepseek_agent import call_deepseek, summarize_text
from managers.diet_agent import build_diet_agent_prompt
from services.language_detection import detect_language
from data.database import db
from config.chat_config import (
    MESSAGES_BEFORE_SUMMARY,
    SUPPORTED_LANGUAGES,
    LANGUAGE_SELECTION_MAP,
    VALIDATION_RULES,
    DEEPSEEK_SETTINGS,
    get_welcome_message,
    get_language_confirmation,
    get_error_message
)

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def process_message(
        self,
        user_id: str,
        message_text: str,
        message_id: str
    ) -> Dict[str, Any]:
        """
        Process an incoming message and generate a response using the diet agent.
        
        Args:
            user_id: The unique identifier for the user
            message_text: The text content of the message
            message_id: The unique identifier for the message
            
        Returns:
            Dict containing the response details
        """
        try:
            # Get or create user profile
            user_profile = await db.get_user_profile(user_id)
            is_new_user = user_profile is None
            
            if is_new_user:
                # Create new user profile with detected language
                detected_lang = await detect_language(message_text)
                user_profile = {
                    "user_id": user_id,
                    "language_code": detected_lang["language_code"],
                    "language_confirmed": False,
                    "onboarding_completed": False,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                await db.update_user_profile(user_id, user_profile)
                
                # Send welcome message in detected language
                welcome_msg = get_welcome_message(detected_lang["language_code"])
                await db.add_message(
                    user_id=user_id,
                    role="assistant",
                    content=welcome_msg
                )
                return {"text": welcome_msg}
            
            # Handle language selection for new users
            if not user_profile.get("language_confirmed", False):
                if message_text in LANGUAGE_SELECTION_MAP:
                    selected_lang = LANGUAGE_SELECTION_MAP[message_text]
                    lang_info = SUPPORTED_LANGUAGES[selected_lang]
                    await db.update_user_profile(
                        user_id=user_id,
                        data={
                            "language_code": selected_lang,
                            "language_confirmed": True,
                            "language": selected_lang,  # For compatibility with diet agent
                            "language_name": lang_info["name"],
                            "is_rtl": lang_info["is_rtl"],
                            "updated_at": datetime.utcnow().isoformat()
                        }
                    )
                    confirmation_msg = get_language_confirmation(selected_lang)
                    await db.add_message(
                        user_id=user_id,
                        role="assistant",
                        content=confirmation_msg
                    )
                    return {"text": confirmation_msg}
                else:
                    # Re-send welcome message if invalid selection
                    welcome_msg = get_welcome_message(user_profile["language_code"])
                    return {"text": welcome_msg}
            
            # Save user message
            await db.add_message(
                user_id=user_id,
                role="user",
                content=message_text
            )
            
            # Maybe update conversation summary
            await self._maybe_update_summary(user_id)
            
            # Get conversation context and history
            context = await db.get_user_context(user_id)
            conversation_summary = context["conversation_summary"] if context else ""
            
            # Build diet agent prompt
            system_prompt = build_diet_agent_prompt(
                user_profile=user_profile,
                conversation_summary=conversation_summary,
                user_language=user_profile.get("language_code")
            )
            
            # Get recent messages for context
            recent_messages = await db.get_recent_messages(user_id, limit=10)
            messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in recent_messages
            ]
            
            # Call DeepSeek with diet agent prompt
            response = await call_deepseek(
                system_prompt=system_prompt,
                user_messages=messages,
                temperature=DEEPSEEK_SETTINGS["default_temperature"]
            )
            
            # Save assistant response
            await db.add_message(
                user_id=user_id,
                role="assistant",
                content=response
            )
            
            # Try to extract and update user info from the message
            await self._try_update_user_info(user_id, message_text, user_profile)
            
            # Update last interaction time
            await db.update_user_profile(
                user_id=user_id,
                data={
                    "last_interaction": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            )
            
            return {"text": response}
            
        except Exception as e:
            self.logger.error(f"Error processing message: {e}", exc_info=True)
            error_msg = get_error_message(user_profile["language_code"] if user_profile else "en")
            return {"text": error_msg}

    async def _maybe_update_summary(self, user_id: str) -> None:
        """
        If we have >= MESSAGES_BEFORE_SUMMARY new messages, generate a summary
        and update conversation_summaries.
        """
        recent_msgs = await db.get_recent_messages(user_id, limit=MESSAGES_BEFORE_SUMMARY)
        if len(recent_msgs) >= MESSAGES_BEFORE_SUMMARY:
            try:
                # Get current context
                current_context = await db.get_user_context(user_id)
                if not current_context:
                    current_context = {
                        "user_id": user_id,
                        "conversation_summary": "",
                        "last_topics": [],
                        "last_interaction": datetime.utcnow().isoformat(),
                        "created_at": datetime.utcnow().isoformat(),
                        "updated_at": datetime.utcnow().isoformat()
                    }

                # Extract messages for summarization
                user_texts = [m["content"] for m in recent_msgs if m["role"] == "user"]
                if not user_texts:
                    return

                # Generate new summary
                partial_summary = await summarize_text(
                    question=DEEPSEEK_SETTINGS["summarization_prompt"],
                    user_answer="\n".join(user_texts)
                )

                # Merge with old summary
                old_summary = current_context.get("conversation_summary", "")
                new_summary = (old_summary + "\n" + partial_summary).strip()

                # Update context
                current_context["conversation_summary"] = new_summary
                current_context["updated_at"] = datetime.utcnow().isoformat()
                await db.update_user_context(user_id, current_context)

            except Exception as e:
                logger.error(f"Error generating summary: {e}")

    async def _try_update_user_info(self, user_id: str, message: str, profile_data: Dict[str, Any]) -> None:
        """Try to extract and update user info from their message."""
        try:
            # Simple number extraction - this could be enhanced with better parsing
            words = message.lower().split()
            
            # Look for numbers that might be age, weight, or height
            for i, word in enumerate(words):
                try:
                    num = float(word.replace("kg", "").replace("cm", "").strip())
                    
                    # Try to determine the type of number based on context
                    if "age" in message.lower() and VALIDATION_RULES["age"]["min"] <= num <= VALIDATION_RULES["age"]["max"]:
                        profile_data["age"] = int(num)
                    elif "height" in message.lower() and VALIDATION_RULES["height_cm"]["min"] <= num <= VALIDATION_RULES["height_cm"]["max"]:
                        profile_data["height_cm"] = int(num)
                    elif "weight" in message.lower() and VALIDATION_RULES["weight"]["min"] <= num <= VALIDATION_RULES["weight"]["max"]:
                        if "target" in message.lower():
                            profile_data["target_weight"] = num
                        else:
                            profile_data["current_weight"] = num
                            
                except ValueError:
                    continue
                    
            # Look for name if it's missing
            if not profile_data.get("first_name") and len(message.split()) <= 5:  # Likely just a name
                name = message.strip().split()[0].title()
                if len(name) >= VALIDATION_RULES["name_min_length"]:
                    profile_data["first_name"] = name

            # Update profile if we found any new information
            if profile_data != await db.get_user_profile(user_id):
                profile_data["updated_at"] = datetime.utcnow().isoformat()
                await db.update_user_profile(user_id, profile_data)
                
        except Exception as e:
            logger.error(f"Error updating user info: {e}")

# Create a single instance
chat_service = ChatService()
