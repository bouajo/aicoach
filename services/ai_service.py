"""
Service for handling AI model interactions.
"""

import os
import logging
from typing import List, Dict, Any
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("Missing DeepSeek API key")
        
        self.api_url = "https://api.deepseek.com/chat/completions"
        self.model = "deepseek-chat"

    async def get_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Get response from the AI model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
        
        Returns:
            str: The AI model's response
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=30.0
                )
                response.raise_for_status()
                
                result = response.json()
                return result["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}", exc_info=True)
            raise

ai_service = AIService()