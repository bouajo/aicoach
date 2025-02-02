"""
DeepSeek agent for chat responses and summaries.
"""

import logging
from typing import Dict, List
from deepseek_client import deepseek_client
from services.conversation_service import conversation_service

logger = logging.getLogger(__name__)

async def call_deepseek(
    system_prompt: str,
    user_messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 300
) -> str:
    """
    Call DeepSeek API to generate a chat response.
    
    Args:
        system_prompt: System prompt to guide the model
        user_messages: List of user message dictionaries
        temperature: Sampling temperature (default: 0.7)
        max_tokens: Maximum tokens to generate (default: 300)
        
    Returns:
        Generated response text
    """
    try:
        # Format messages for DeepSeek API
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(user_messages)

        # Call DeepSeek API
        response = await deepseek_client.create_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Extract and return the response text
        return response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.error(f"Error calling DeepSeek API: {e}")
        raise

async def summarize_text(question: str, user_answer: str) -> str:
    """
    Summarize text using DeepSeek.
    
    Args:
        question: Context question
        user_answer: Text to summarize
        
    Returns:
        Generated summary
    """
    try:
        system_prompt = (
            "You are a precise summarizer. Create a concise summary that captures "
            "the key points while maintaining context and important details."
        )
        
        messages = [{
            "role": "user",
            "content": f"Question: {question}\nText to summarize: {user_answer}"
        }]

        # Call DeepSeek API with lower temperature for more focused summary
        response = await deepseek_client.create_chat_completion(
            messages=[{"role": "system", "content": system_prompt}] + messages,
            temperature=0.3,  # Lower temperature for more focused output
            max_tokens=150  # Limit summary length
        )

        return response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.error(f"Error summarizing text: {e}")
        raise
