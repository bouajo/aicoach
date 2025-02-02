"""
DeepSeek API client implementation using httpx.
"""

import os
import httpx
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY environment variable is not set")

class DeepSeekClient:
    def __init__(self):
        self.base_url = "https://api.deepseek.com/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

    async def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Create a chat completion using DeepSeek's API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (default: deepseek-chat)
            temperature: Sampling temperature (default: 0.7)
            max_tokens: Maximum tokens to generate (optional)
            stream: Whether to stream the response (default: False)
            
        Returns:
            API response as a dictionary
        """
        try:
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": stream
            }
            if max_tokens:
                data["max_tokens"] = max_tokens

            response = await self.client.post("/chat/completions", json=data)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating chat completion: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

# Create a single global instance
deepseek_client = DeepSeekClient()
