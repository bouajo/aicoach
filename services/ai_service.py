"""
Service for interacting with AI (DeepSeek).
"""

import logging
from typing import List, Dict, Any
from deepseek_agent import call_deepseek

logger = logging.getLogger(__name__)

class AIService:
    async def get_response(
        self, 
        system_prompt: str, 
        conversation_history: List[Dict[str, str]], 
        user_data: Dict[str, Any] = None
    ) -> str:
        """
        Get an AI response based on system prompt and conversation history.
        
        Args:
            system_prompt: System instructions for the AI
            conversation_history: List of previous messages
            user_data: Optional user data for context
            
        Returns:
            Generated AI response
        """
        try:
            # Add user context if available
            context = ""
            if user_data:
                context = f"\nUser Context:\n"
                for key, value in user_data.items():
                    if key not in ["user_id", "created_at", "updated_at"]:
                        context += f"- {key}: {value}\n"
                system_prompt = f"{system_prompt}\n{context}"
            
            return await call_deepseek(system_prompt, conversation_history)
        except Exception as e:
            logger.error(f"Error get_response AI: {e}", exc_info=True)
            return "Sorry, an error occurred. Please try again later."

ai_service = AIService()