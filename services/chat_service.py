# file: services/chat_service.py

"""
Chat service for managing conversations (data collection, AI invocation, etc.).
"""

import logging
from typing import Tuple, Dict, Any
from data.models import UserProfile, ConversationState
from data.database import db
from managers import prompt_manager, flow_manager
from services.conversation_service import conversation_service
from services.ai_service import ai_service

logger = logging.getLogger(__name__)

class ChatService:
    def _normalize_state(self, state: str) -> str:
        """Normalize conversation state to lowercase."""
        return state.lower() if state else "introduction"

    async def process_message(
        self, user_id: str, message: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Main method for processing a user message.
        Returns (response, user_data).
        """
        try:
            # Get or create user profile
            profile_data = await db.get_user_profile(user_id)
            if not profile_data:
                # New user - send introduction message
                profile_data = {
                    "user_id": user_id, 
                    "conversation_state": "introduction",
                    "language": "en"  # Start with English for the introduction
                }
                await db.update_user_profile(user_id, profile_data)
                # Use the comprehensive introduction that explains what data will be collected
                intro_message = (
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
                return intro_message, profile_data

            # Get current state and language
            state_str = self._normalize_state(profile_data.get("conversation_state", "introduction"))
            try:
                current_state = ConversationState(state_str)
            except ValueError as e:
                logger.error(f"Invalid state '{state_str}' for user {user_id}, resetting to introduction")
                current_state = ConversationState.INTRODUCTION
                profile_data["conversation_state"] = current_state.value
                await db.update_user_profile(user_id, {"conversation_state": current_state.value})

            language = profile_data.get("language", "en")
            
            # Save incoming message
            await conversation_service.add_message(user_id, "user", message)

            # Process based on state
            if current_state == ConversationState.INTRODUCTION:
                next_state = ConversationState.LANGUAGE_SELECTION
                profile_data["conversation_state"] = next_state.value
                await db.update_user_profile(user_id, {"conversation_state": next_state.value})
                return prompt_manager.get_message_template(next_state, language), profile_data
                
            elif current_state == ConversationState.LANGUAGE_SELECTION:
                # Handle language selection with more flexible matching
                msg_lower = message.lower().strip()
                
                # More comprehensive language detection
                if any(eng in msg_lower for eng in ["english", "en", "anglais", "eng", "🇬🇧"]):
                    profile_data["language"] = "en"
                    language = "en"
                elif any(fr in msg_lower for fr in ["french", "fr", "français", "francais", "🇫🇷"]):
                    profile_data["language"] = "fr"
                    language = "fr"
                else:
                    # Invalid language choice - ask again with clearer instructions
                    return (
                        "I didn't catch that. Please specify your language preference:\n"
                        "- For English, type: English\n"
                        "- Pour le français, tapez : Français"
                    ), profile_data
                
                # Update language and move to name collection
                await db.update_user_profile(user_id, {"language": language})
                next_state = ConversationState.NAME_COLLECTION
                profile_data["conversation_state"] = next_state.value
                await db.update_user_profile(user_id, {"conversation_state": next_state.value})
                
                # Get the appropriate welcome message based on language
                welcome_msg = (
                    "Perfect! We'll continue in English. To begin, I'd like to learn more about you."
                    if language == "en"
                    else "Parfait ! Nous continuerons en français. Pour commencer, j'aimerais en savoir plus sur vous."
                )
                
                # Get the name collection prompt
                name_prompt = prompt_manager.get_message_template(next_state, language)
                return f"{welcome_msg}\n\n{name_prompt}", profile_data
            
            elif current_state in [
                ConversationState.NAME_COLLECTION,
                ConversationState.AGE_COLLECTION,
                ConversationState.HEIGHT_COLLECTION,
                ConversationState.START_WEIGHT_COLLECTION,
                ConversationState.GOAL_COLLECTION,
                ConversationState.TARGET_DATE_COLLECTION
            ]:
                # Data collection phase
                state_to_field = {
                    ConversationState.NAME_COLLECTION: "first_name",
                    ConversationState.AGE_COLLECTION: "age",
                    ConversationState.HEIGHT_COLLECTION: "height_cm",
                    ConversationState.START_WEIGHT_COLLECTION: "current_weight",
                    ConversationState.GOAL_COLLECTION: "target_weight",
                    ConversationState.TARGET_DATE_COLLECTION: "target_date"
                }
                
                field = state_to_field.get(current_state)
                updated_data = flow_manager.extract_and_validate_field(current_state, message, profile_data)
                
                if updated_data:
                    # Mise à jour réussie
                    profile_data.update(updated_data)
                    await db.update_user_profile(user_id, updated_data)
                    logger.info(f"Updated {field} for user {user_id}: {updated_data}")
                    
                    # Get next state
                    next_state = current_state.next_state()
                    if next_state != current_state:
                        profile_data["conversation_state"] = next_state.value
                        await db.update_user_profile(user_id, {"conversation_state": next_state.value})
                        # Create a copy of profile_data without the language field
                        template_data = {k: v for k, v in profile_data.items() if k != 'language'}
                        response = prompt_manager.get_message_template(next_state, language, **template_data)
                        if not response:
                            logger.error(f"Failed to get template for state {next_state}")
                            response = "Please continue with the next step." if language == "en" else "Veuillez continuer avec l'étape suivante."
                        return response, profile_data
                    else:
                        # All data collected - move to preferences
                        next_state = ConversationState.DIET_PREFERENCES
                        profile_data["conversation_state"] = next_state.value
                        await db.update_user_profile(user_id, {"conversation_state": next_state.value})
                        return prompt_manager.get_message_template(next_state, language), profile_data
                else:
                    # Validation failed - get specific error message
                    error_msg = prompt_manager.get_validation_error(field, language)
                    logger.warning(f"Validation failed for {field} - user {user_id}: {message}")
                    # Create template data without language field
                    template_data = {k: v for k, v in profile_data.items() if k != 'language'}
                    current_prompt = prompt_manager.get_message_template(current_state, language, **template_data)
                    return f"{error_msg}\n\n{current_prompt}", profile_data
                
            elif current_state == ConversationState.DIET_PREFERENCES:
                # Save preferences and move to restrictions
                profile_data["diet_preferences"] = message
                next_state = current_state.next_state()
                profile_data["conversation_state"] = next_state.value  # This will be lowercase
                await db.update_user_profile(user_id, profile_data)
                return prompt_manager.get_message_template(next_state, language), profile_data
                
            elif current_state == ConversationState.DIET_RESTRICTIONS:
                # Save restrictions and move to planning
                profile_data["diet_restrictions"] = message
                next_state = current_state.next_state()
                profile_data["conversation_state"] = next_state.value  # This will be lowercase
                await db.update_user_profile(user_id, profile_data)
                
                # Generate initial diet plan
                system_prompt = prompt_manager.get_system_prompt("diet_planning", language)
                recent_messages = await conversation_service.get_recent_messages(user_id, limit=5)
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in recent_messages
                ]
                
                response = await ai_service.get_response(
                    system_prompt=system_prompt,
                    conversation_history=conversation_history,
                    user_data=profile_data
                )
                return response, profile_data
                
            else:
                # Free chat mode - use AI
                system_prompt = prompt_manager.get_system_prompt("base", language)
                recent_messages = await conversation_service.get_recent_messages(user_id, limit=5)
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in recent_messages
                ]
                
                response = await ai_service.get_response(
                    system_prompt=system_prompt,
                    conversation_history=conversation_history,
                    user_data=profile_data
                )

        except Exception as e:
            logger.error(f"Error processing message for user {user_id}: {str(e)}", exc_info=True)
            return "Je suis désolé, une erreur s'est produite. Veuillez réessayer.", {}

        # Save response
        await conversation_service.add_message(user_id, "assistant", response)
        return response, profile_data

chat_service = ChatService()
