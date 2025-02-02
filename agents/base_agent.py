"""
Base agent class for all AI agents in the system.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime
from data.database import db

class BaseAgent(ABC):
    """Base class for all AI agents."""
    
    def __init__(self, user_id: str):
        """Initialize the base agent.
        
        Args:
            user_id: The unique identifier for the user
        """
        self.user_id = user_id
        self.context: Dict[str, Any] = {}
        
    @abstractmethod
    async def process_message(self, message_text: str, phone_number: Optional[str] = None) -> str:
        """Process a message from the user.
        
        This method should be implemented by subclasses.
        
        Args:
            message_text: The text message from the user
            phone_number: Optional phone number of the user
            
        Returns:
            str: The response message to send back to the user
        """
        raise NotImplementedError("Subclasses must implement process_message")
        
    @abstractmethod
    def build_system_prompt(self) -> str:
        """Build the system prompt for the agent."""
        pass
        
    async def get_conversation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history."""
        return await db.get_recent_messages(self.user_id, limit)
        
    def get_user_profile(self) -> Dict[str, Any]:
        """Get the user's profile from the database.
        
        Returns:
            Dict[str, Any]: The user's profile data
        """
        return db.get_user_profile(self.user_id)
        
    def update_user_profile(self, data: Dict[str, Any]) -> bool:
        """Update the user's profile in the database.
        
        Args:
            data: The data to update in the profile
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        return db.update_user_profile(self.user_id, data)
        
    async def save_message(self, role: str, content: str) -> bool:
        """Save a message to the conversation history."""
        return await db.add_message(self.user_id, role, content)
        
    async def get_context(self) -> Optional[Dict[str, Any]]:
        """Get the user's context."""
        return await db.get_user_context(self.user_id)
        
    async def update_context(self, data: Dict[str, Any]) -> bool:
        """Update the user's context."""
        return await db.update_user_context(self.user_id, data) 