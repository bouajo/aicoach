"""
Manages all prompts for the conversation flow, ensuring consistency and proper state transitions.
"""

from typing import Dict, Any, Optional
from data.models import ConversationState
from prompts import introduction, diet_plan, follow_up
import logging

logger = logging.getLogger(__name__)

class PromptManager:
    def get_system_prompt(self, language: str, current_state: ConversationState, context: Dict[str, Any]) -> str:
        """
        Get the system prompt for the current state.
        """
        base_prompt = (
            "You are Eric, a supportive nutrition coach with over 20 years of experience.\n"
            f"Current conversation state: {current_state.value}\n"
            f"You MUST respond in: {language}\n\n"
            "Core principles:\n"
            "1. Be empathetic and supportive\n"
            "2. Use culturally appropriate language and examples\n"
            "3. Keep responses clear and concise\n"
            "4. Always maintain the persona of Eric\n"
            "5. Focus on healthy, sustainable approaches\n\n"
        )

        # Add state-specific instructions
        if current_state == ConversationState.INTRODUCTION:
            base_prompt += introduction.get_system_instructions(language)
        elif current_state == ConversationState.PLAN_GENERATION:
            base_prompt += diet_plan.get_system_instructions(language)
        elif current_state == ConversationState.FREE_CHAT:
            base_prompt += follow_up.get_system_instructions(language)

        return base_prompt

    def get_user_prompt(
        self,
        current_state: ConversationState, 
        language: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get the appropriate prompt for the current conversation state.
        """
        try:
            if current_state == ConversationState.INTRODUCTION:
                return introduction.get_introduction_prompt(language)
            
            # For data collection states, use the appropriate prompt
            data_collection_states = {
                ConversationState.NAME_COLLECTION: "first_name",
                ConversationState.AGE_COLLECTION: "age",
                ConversationState.HEIGHT_COLLECTION: "height_cm",
                ConversationState.START_WEIGHT_COLLECTION: "current_weight",
                ConversationState.GOAL_COLLECTION: "target_weight",
                ConversationState.TARGET_DATE_COLLECTION: "target_date",
                ConversationState.DIET_PREFERENCES: "diet_preferences",
                ConversationState.DIET_RESTRICTIONS: "diet_restrictions"
            }
            
            if current_state in data_collection_states:
                return introduction.get_data_collection_prompt(
                    data_collection_states[current_state],
                    language,
                    context
                )
            
            # For plan generation and review
            if current_state == ConversationState.PLAN_GENERATION:
                return diet_plan.get_plan_prompt(language, context)
            elif current_state == ConversationState.PLAN_REVIEW:
                return diet_plan.get_review_prompt(language, context)
            
            # For follow-up conversations
            if current_state == ConversationState.FREE_CHAT:
                return follow_up.get_chat_prompt(language, context)
                
            logger.warning(f"No specific prompt found for state {current_state}")
            return ""
            
        except Exception as e:
            logger.error(f"Error getting prompt for state {current_state}: {e}")
            return ""

    def get_analysis_prompt(
        self, 
        current_state: ConversationState,
        message: str,
        language: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get the analysis prompt for validating user input.
        """
        base_prompt = (
            f"Analyze the following user response for {current_state.value}.\n\n"
            "Context:\n"
            f"- User's message: {message}\n"
            f"- Current state: {current_state.value}\n"
            f"- User's language: {language}\n\n"
            )

        if context:
            base_prompt += "User's current data:\n"
            for key, value in context.items():
                if key not in ["user_id", "conversation_state", "language"]:
                    base_prompt += f"- {key}: {value}\n"

        base_prompt += "\nInstructions:\n"
        base_prompt += "1. Extract and validate the relevant information\n"
        base_prompt += "2. Return a JSON with:\n"
        base_prompt += "   - is_valid: boolean\n"
        base_prompt += "   - value: extracted value (number, text, or list)\n"
        base_prompt += "   - error: error message in user's language if invalid\n\n"

        # Add state-specific validation rules
        validation_rules = {
            ConversationState.NAME_COLLECTION: "- Must be a real name (min 2 chars)\n- Should not contain numbers or special characters",
            ConversationState.AGE_COLLECTION: "- Must be between 13-100 years\n- Convert text numbers to numeric",
            ConversationState.HEIGHT_COLLECTION: "- Must be between 100-250 cm\n- Convert different formats (e.g., '1m75' to 175)",
            ConversationState.START_WEIGHT_COLLECTION: "- Must be between 30-300 kg\n- Convert different formats and units",
            ConversationState.GOAL_COLLECTION: "- Must be between 30-300 kg\n- Must be realistic compared to current weight",
            ConversationState.TARGET_DATE_COLLECTION: "- Convert time expressions to number of weeks\n- Must be between 4-52 weeks",
            ConversationState.DIET_PREFERENCES: "- Extract and categorize dietary preferences\n- Convert to list format",
            ConversationState.DIET_RESTRICTIONS: "- Extract and categorize restrictions and allergies\n- Convert to list format"
        }

        if current_state in validation_rules:
            base_prompt += f"Validation rules:\n{validation_rules[current_state]}"

        return base_prompt

    def get_error_prompt(self, language: str) -> str:
        """
        Get the error prompt for generating error messages.
        """
        return (
            f"Generate a polite error message asking the user to try again.\n"
            f"MUST be in {language}.\n"
            "Be encouraging and supportive."
        )

# Create a single global instance
prompt_manager = PromptManager()