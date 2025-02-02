# file: services/chat_service.py

import logging
from typing import Tuple, Dict, Any, List
from data.models import UserProfile, ConversationState
from data.database import db
from services.conversation_service import conversation_service
from services.language_detection import detect_language
from managers.prompt_manager import prompt_manager
from deepseek_agent import call_deepseek, summarize_text
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MESSAGES_BEFORE_SUMMARY = 5  # Number of messages before creating a new summary

class ChatService:
    async def _update_conversation_summary(self, user_id: str, recent_messages: List[Dict[str, Any]]) -> None:
        """
        Update the conversation summary in the user context.
        
        Args:
            user_id: User ID
            recent_messages: List of recent messages
        """
        try:
            # Extract user messages only
            user_texts = [m.content for m in recent_messages if m.role == "user"]
            if not user_texts:
                return
                
            full_user_text = "\n".join(user_texts)
            
            # Generate new summary
            partial_summary = await summarize_text(
                question="User's conversation so far",
                user_answer=full_user_text
            )
            
            # Get current context and merge summaries
            current_context = await db.get_user_context(user_id) or {}
            old_summary = current_context.get("conversation_summary", "")
            
            # Merge summaries, keeping only the most relevant parts
            new_summary = old_summary + "\n" + partial_summary if old_summary else partial_summary
            
            # Update context with new summary
            current_context["conversation_summary"] = new_summary.strip()
            await db.update_user_context(user_id, current_context)
            
        except Exception as e:
            logger.error(f"Error updating conversation summary: {e}", exc_info=True)

    async def _get_response_with_context(
        self,
        user_id: str,
        message: str,
        language: str,
        current_state: ConversationState
    ) -> str:
        try:
            user_context = await db.get_user_context(user_id) or {}
            conversation_summary = user_context.get("conversation_summary", "")
            
            # Get system prompt from prompt manager
            system_prompt = prompt_manager.get_system_prompt(
                language=language,
                current_state=current_state,
                context={
                    "conversation_summary": conversation_summary,
                    **user_context
                }
            )
            
            messages = [{"role": "user", "content": message}]
            return await call_deepseek(system_prompt, messages)
            
        except Exception as e:
            logger.error(f"Error getting response with context: {e}", exc_info=True)
            return await call_deepseek(prompt_manager.get_error_prompt(language), [])

    async def _analyze_user_response(
        self,
        message: str,
        current_state: ConversationState,
        language: str,
        context: Dict[str, Any]
    ) -> Tuple[bool, Any, str]:
        """
        Analyze user response using DeepSeek and extract relevant information.
        """
        try:
            analysis_prompt = prompt_manager.get_analysis_prompt(
                current_state=current_state,
                message=message,
                language=language,
                context=context
            )
            
            analysis_result = await call_deepseek(analysis_prompt, [{"role": "user", "content": message}])
            try:
                result = json.loads(analysis_result)
                return result["is_valid"], result["value"], result.get("error", "")
            except:
                logger.error(f"Failed to parse analysis result: {analysis_result}")
                return False, None, await call_deepseek(prompt_manager.get_error_prompt(language), [])
                
        except Exception as e:
            logger.error(f"Error analyzing user response: {e}", exc_info=True)
            return False, None, await call_deepseek(prompt_manager.get_error_prompt(language), [])

    async def _ensure_user_exists(self, user_id: str) -> Dict[str, Any]:
        """
        Ensure user exists in database, create if not.
        
        Args:
            user_id: User ID
            
        Returns:
            User profile data
        """
        try:
            # Try to get existing user
            profile_data = await db.get_user_profile(user_id)
            if profile_data:
                return profile_data

            # Create new user with minimal data
            new_profile = {
                "user_id": user_id,
                "conversation_state": ConversationState.LANGUAGE_DETECTION.value,
                "language": "en",  # Default to English until detected
                "language_name": "English",
                "is_rtl": False
            }
            
            # Ensure user is created before proceeding
            success = await db.update_user_profile(user_id, new_profile)
            if not success:
                logger.error(f"Failed to create user profile for {user_id}")
                raise ValueError("Failed to create user profile")
                
            # Get the created profile
            profile_data = await db.get_user_profile(user_id)
            if not profile_data:
                logger.error(f"Failed to retrieve created user profile for {user_id}")
                raise ValueError("Failed to retrieve created user profile")
                
            return profile_data
            
        except Exception as e:
            logger.error(f"Error ensuring user exists: {e}", exc_info=True)
            # Return a default profile in case of error
            return {
                "user_id": user_id,
                "conversation_state": ConversationState.LANGUAGE_DETECTION.value,
                "language": "en",
                "language_name": "English",
                "is_rtl": False
            }

    async def _maybe_update_summary(self, user_id: str) -> None:
        """
        Check if we need to update the conversation summary and do so if needed.
        
        Args:
            user_id: User ID
        """
        try:
            recent_messages = await conversation_service.get_recent_messages(user_id, limit=MESSAGES_BEFORE_SUMMARY)
            if len(recent_messages) >= MESSAGES_BEFORE_SUMMARY:
                await self._update_conversation_summary(user_id, recent_messages)
        except Exception as e:
            logger.error(f"Error checking/updating summary: {e}", exc_info=True)

    async def process_message(self, user_id: str, message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process an incoming message from a user.
        
        Args:
            user_id: The user's ID
            message: The message content
            
        Returns:
            Tuple[str, Dict[str, Any]]: The response message and updated user profile
        """
        try:
            profile_data = await self._ensure_user_exists(user_id)
            current_state = ConversationState(profile_data.get("conversation_state", "language_detection"))
            language = profile_data.get("language", "en")

            # Store message
            await conversation_service.add_message(user_id, "user", message)
            
            # Maybe update summary if enough messages
            await self._maybe_update_summary(user_id)

            # Handle language detection
            if current_state == ConversationState.LANGUAGE_DETECTION:
                # Get full language details
                language_details = await detect_language(message)
                
                # Update profile with language information
                profile_data["language"] = language_details["language_code"]
                profile_data["language_name"] = language_details["language_name"]
                profile_data["is_rtl"] = language_details["is_rtl"]
                profile_data["conversation_state"] = ConversationState.INTRODUCTION.value
                await db.update_user_profile(user_id, profile_data)
                
                # Get introduction prompt
                response = prompt_manager.get_user_prompt(
                    current_state=ConversationState.INTRODUCTION,
                    language=language_details["language_code"],
                    context=profile_data
                )
                
                if not response:  # Fallback to DeepSeek if no template
                    # Include language details in the system prompt
                    system_prompt = prompt_manager.get_system_prompt(
                        language=language_details["language_code"],
                        current_state=ConversationState.INTRODUCTION,
                        context={
                            **profile_data,
                            "language_name": language_details["language_name"],
                            "is_rtl": language_details["is_rtl"]
                        }
                    )
                    response = await call_deepseek(system_prompt, [])
                
                await conversation_service.add_message(user_id, "assistant", response)
                return response, profile_data

            # For all other states, analyze the response first
            is_valid, extracted_value, error_message = await self._analyze_user_response(
                message=message,
                current_state=current_state,
                language=language,
                context=profile_data
            )
            
            if not is_valid:
                return error_message, profile_data

            # Update profile with extracted value
            if current_state == ConversationState.NAME_COLLECTION:
                profile_data["first_name"] = extracted_value
            elif current_state == ConversationState.AGE_COLLECTION:
                profile_data["age"] = extracted_value
            elif current_state == ConversationState.HEIGHT_COLLECTION:
                profile_data["height_cm"] = extracted_value
            elif current_state == ConversationState.START_WEIGHT_COLLECTION:
                profile_data["start_weight"] = extracted_value
                profile_data["current_weight"] = extracted_value
            elif current_state == ConversationState.GOAL_COLLECTION:
                profile_data["target_weight"] = extracted_value
            elif current_state == ConversationState.TARGET_DATE_COLLECTION:
                target_date = datetime.now() + timedelta(weeks=extracted_value)
                profile_data["target_date"] = target_date.date().isoformat()
            elif current_state == ConversationState.DIET_PREFERENCES:
                profile_data["diet_preferences"] = extracted_value
            elif current_state == ConversationState.DIET_RESTRICTIONS:
                profile_data["diet_restrictions"] = extracted_value

            # Move to next state
            next_state = current_state.next_state()
            profile_data["conversation_state"] = next_state.value
            await db.update_user_profile(user_id, profile_data)

            # Get next prompt from prompt manager
            response = prompt_manager.get_user_prompt(
                current_state=next_state,
                language=language,
                context=profile_data
            )
            
            if not response:  # Fallback to DeepSeek if no template
                system_prompt = prompt_manager.get_system_prompt(
                    language=language,
                    current_state=next_state,
                    context={
                        **profile_data,
                        "language_name": profile_data.get("language_name", "Unknown"),
                        "is_rtl": profile_data.get("is_rtl", False)
                    }
                )
                response = await call_deepseek(system_prompt, [])
            
            await conversation_service.add_message(user_id, "assistant", response)
            return response, profile_data

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            # Return a default error response in English
            error_response = "I encountered an error. Please try again."
            return error_response, profile_data or {
                "user_id": user_id,
                "language": "en",
                "conversation_state": ConversationState.LANGUAGE_DETECTION.value
            }

# Create a single global instance
chat_service = ChatService()
