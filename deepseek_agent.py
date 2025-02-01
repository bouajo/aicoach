"""
Client/Agent spécifique DeepSeek pour la génération de réponses et pour résumés.
"""

import os
import logging
import json
from typing import Dict, List
from dotenv import load_dotenv
from openai import AsyncOpenAI  # Selon votre implémentation DeepSeek
from services.conversation_service import conversation_service

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize the DeepSeek client
deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"  # URL de l'API DeepSeek, adapter si nécessaire
)

# Example default system prompt for a "coach"
COACH_PROMPT = """
Tu es un coach nutritionnel expérimenté. Sois chaleureux, empathique, et pose des questions pour recueillir les infos manquantes. Donne des conseils personnalisés.
"""

async def call_deepseek(
    system_prompt: str,
    user_messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 300
) -> str:
    """
    Appelle l'API DeepSeek pour générer une réponse de chat.
    """
    try:
        messages = [{"role": "system", "content": system_prompt}] + user_messages
        response = await deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return "Désolé, j'ai rencontré un problème en générant la réponse."

async def ask_coach_response(user_id: str, user_text: str) -> str:
    """
    Exemple de fonction pour générer une réponse du coach en se basant sur l'historique de la conversation.
    """
    try:
        # Store user's message
        await conversation_service.add_message(user_id, "user", user_text)

        # Retrieve recent messages
        recent_messages = await conversation_service.get_recent_messages(user_id, limit=5)
        messages_for_api = [{"role": m.role, "content": m.content} for m in recent_messages]

        # Generate response
        reply = await call_deepseek(COACH_PROMPT, messages_for_api)
        
        # Store the assistant response
        await conversation_service.add_message(user_id, "assistant", reply)
        return reply

    except Exception as e:
        logger.error(f"Error in ask_coach_response: {e}")
        return "Je suis désolé, j'ai rencontré un problème."

#
# NEW FUNCTION FOR SUMMARIZATION
#
async def summarize_text(question: str, user_answer: str) -> str:
    """
    Calls DeepSeek (or any LLM) to produce a short summary of the user's answer.
    This can be used to store condensed info in your DB.
    """
    try:
        system_prompt = (
            "Tu es un assistant spécialisé dans la synthèse de réponses courtes et claires. "
            "Résume brièvement la réponse de l'utilisateur."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Question: {question}\nAnswer: {user_answer}\n\nRésumé :" }
        ]
        # We can reduce max_tokens to ensure we get a short summary
        response = await deepseek_client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=0.5,
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"DeepSeek summarization error: {e}")
        return "Unable to summarize."
