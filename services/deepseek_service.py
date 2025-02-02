"""
Service for interacting with DeepSeek's API.
"""

import os
import logging
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DeepseekService:
    """Service for interacting with DeepSeek's API."""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is required")
            
        self.api_base = "https://api.deepseek.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.api_base,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
        
    async def chat_completion(
        self,
        system_prompt: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Generate a chat completion using DeepSeek's API.
        
        Args:
            system_prompt: The system prompt to guide the model's behavior
            messages: List of conversation messages
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum tokens in the response
            
        Returns:
            str: The generated response
        """
        try:
            # Prepare the messages
            formatted_messages = [{"role": "system", "content": system_prompt}]
            formatted_messages.extend(messages)
            
            # Make API call
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": "deepseek-chat",
                    "messages": formatted_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            response.raise_for_status()
            
            # Extract and return the response text
            result = response.json()
            if not result.get("choices"):
                raise ValueError("No response choices returned from API")
                
            return result["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"Error in chat completion: {e}")
            raise
            
    async def summarize_text(
        self,
        text: str,
        prompt: Optional[str] = None,
        max_tokens: int = 200
    ) -> str:
        """
        Summarize a piece of text using DeepSeek's API.
        
        Args:
            text: The text to summarize
            prompt: Optional custom prompt for summarization
            max_tokens: Maximum tokens in the summary
            
        Returns:
            str: The generated summary
        """
        default_prompt = "Please provide a concise summary of the following conversation, focusing on key points and any decisions or actions:"
        system_prompt = prompt or default_prompt
        
        try:
            response = await self.chat_completion(
                system_prompt=system_prompt,
                messages=[{"role": "user", "content": text}],
                temperature=0.3,  # Lower temperature for more focused summaries
                max_tokens=max_tokens
            )
            return response
            
        except Exception as e:
            logger.error(f"Error in text summarization: {e}")
            raise
            
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

# Create a single instance
deepseek = DeepseekService() 