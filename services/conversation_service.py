"""
Service for managing conversation history and messages.
"""

import logging
from typing import Dict, Any, List, Optional
from data.database import db
from datetime import datetime

logger = logging.getLogger(__name__)

class ConversationService:
    async def add_message(self, user_id: str, role: str, content: str) -> bool:
        """
        Add a message to the conversation history.
        
        Args:
            user_id: The user's ID
            role: Message role (user/assistant)
            content: Message content
            
        Returns:
            bool: True if successful
        """
        try:
            return await db.add_message(user_id, role, content)
        except Exception as e:
            logger.error(f"Error adding message for {user_id}: {e}", exc_info=True)
            return False

    async def get_recent_messages(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent messages for a user.
        
        Args:
            user_id: The user's ID
            limit: Maximum number of messages to return
            
        Returns:
            List[Dict[str, Any]]: List of recent messages
        """
        try:
            return await db.get_recent_messages(user_id, limit)
        except Exception as e:
            logger.error(f"Error getting recent messages for {user_id}: {e}", exc_info=True)
            return []

    async def get_conversation_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get conversation history for a user.
        
        Args:
            user_id: The user's ID
            limit: Maximum number of messages to return
            
        Returns:
            List[Dict[str, Any]]: List of messages in chronological order
        """
        try:
            return await db.get_conversation_history(user_id, limit)
        except Exception as e:
            logger.error(f"Error getting conversation history for {user_id}: {e}", exc_info=True)
            return []

    async def clear_history(self, user_id: str) -> bool:
        """
        Clear conversation history for a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            bool: True if successful
        """
        try:
            return await db.delete_conversation_history(user_id)
        except Exception as e:
            logger.error(f"Error clearing history for {user_id}: {e}", exc_info=True)
            return False

# Create a single instance
conversation_service = ConversationService() 