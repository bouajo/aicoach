"""
Service for managing conversation history (database read/write).
"""

import logging
from typing import List, Dict, Any, Optional
from data.models import ConversationMessage, UserProfile
from data.database import db

logger = logging.getLogger(__name__)

class ConversationService:
    async def add_message(self, user_id: str, role: str, content: str) -> None:
        """
        Add a message to the conversation history.
        
        Args:
            user_id: User ID
            role: Message role (user/assistant)
            content: Message content
        """
        try:
            message = ConversationMessage(
                user_id=user_id,
                role=role,
                content=content
            )
            await db.add_conversation_message(message)
        except Exception as e:
            logger.error(f"Error adding message for {user_id}: {e}", exc_info=True)

    async def get_recent_messages(
        self, user_id: str, limit: int = 5
    ) -> List[ConversationMessage]:
        """
        Get recent messages from a conversation.
        
        Args:
            user_id: User ID
            limit: Maximum number of messages to return
            
        Returns:
            List of recent messages
        """
        try:
            rows = await db.get_conversation_history(user_id, limit)
            return [ConversationMessage(**r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting messages for {user_id}: {e}", exc_info=True)
            return []

    async def get_conversation_summary(self, user_id: str) -> str:
        """
        Generate a summary of the user's recent messages.
        
        Args:
            user_id: User ID
            
        Returns:
            Summary of messages
        """
        try:
            messages = await self.get_recent_messages(user_id, limit=3)
            user_messages = [
                msg.content for msg in messages 
                if msg.role == "user"
            ]
            return "\n".join(user_messages)
        except Exception as e:
            logger.error(f"Error getting summary for {user_id}: {e}", exc_info=True)
            return ""

    async def clear_conversation_history(self, user_id: str) -> None:
        """
        Clear a user's conversation history.
        
        Args:
            user_id: User ID
        """
        try:
            await db.delete_conversation_history(user_id)
        except Exception as e:
            logger.error(f"Error clearing history for {user_id}: {e}", exc_info=True)

    async def get_messages_by_state(
        self, user_id: str, state: str, limit: int = 5
    ) -> List[ConversationMessage]:
        """
        Get conversation messages for a specific state.
        
        Args:
            user_id: User ID
            state: Conversation state
            limit: Maximum number of messages
            
        Returns:
            List of messages for the state
        """
        try:
            rows = await db.get_messages_by_state(user_id, state, limit)
            return [ConversationMessage(**r) for r in rows]
        except Exception as e:
            logger.error(f"Error getting messages by state for {user_id}: {e}", exc_info=True)
            return []

conversation_service = ConversationService() 