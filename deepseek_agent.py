"""
Client/Agent spécifique DeepSeek pour la génération de réponses.
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

# Initialiser le client DeepSeek
deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"  # URL de l'API DeepSeek, à adapter
)

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
    Appelle l'API DeepSeek pour générer une réponse.
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
    Génère une réponse du coach en se basant sur l'historique de la conversation.
    """
    try:
        # Ajouter le message user dans l'historique
        await conversation_service.add_message(user_id, "user", user_text)

        # Récupérer les derniers messages
        recent_messages = await conversation_service.get_recent_messages(user_id, limit=5)
        messages_for_api = [{"role": m.role, "content": m.content} for m in recent_messages]

        # Générer la réponse
        reply = await call_deepseek(COACH_PROMPT, messages_for_api)
        
        # Sauvegarder la réponse
        await conversation_service.add_message(user_id, "assistant", reply)

        return reply
    except Exception as e:
        logger.error(f"Error in ask_coach_response: {e}")
        return "Je suis désolé, j'ai rencontré un problème."
