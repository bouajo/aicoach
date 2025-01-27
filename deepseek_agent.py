"""
DeepSeek AI agent for conversation handling.
"""

import os
import logging
import json
from typing import Dict, List, Any
from dotenv import load_dotenv
from openai import AsyncOpenAI

from data.database import db
from services.conversation_service import conversation_service

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize DeepSeek client
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

########################
# PROMPTS
########################
COACH_PROMPT = """
[Keep your existing COACH_PROMPT content unchanged]
"""

########################
# DeepSeek Helpers
########################

async def _call_deepseek(
    system_prompt: str,
    user_messages: List[Dict[str, str]],
    temperature=0.7,
    max_tokens=300
) -> str:
    """
    Appelle l'API DeepSeek pour générer une réponse.
    
    Args:
        system_prompt: Prompt système pour le contexte
        user_messages: Liste des messages de la conversation
        temperature: Paramètre de créativité
        max_tokens: Nombre maximum de tokens dans la réponse
        
    Returns:
        Réponse générée par le modèle
    """
    try:
        messages = [{"role": "system", "content": system_prompt}] + user_messages
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return "Désolé, j'ai rencontré un problème en générant la réponse."

########################
# Main Functions
########################

async def ask_coach_response(user_id: str, user_text: str) -> str:
    """
    Génère une réponse du coach en utilisant l'historique des conversations.
    
    Args:
        user_id: ID de l'utilisateur
        user_text: Message de l'utilisateur
        
    Returns:
        Réponse du coach
    """
    try:
        # Ajoute le message de l'utilisateur à l'historique
        await conversation_service.add_message(user_id, "user", user_text)
        
        # Récupère les messages récents
        recent_messages = await conversation_service.get_recent_messages(user_id, limit=5)
        messages_for_api = [{"role": msg.role, "content": msg.content} for msg in recent_messages]

        # Génère la réponse
        assistant_reply = await _call_deepseek(
            system_prompt=COACH_PROMPT,
            user_messages=messages_for_api
        )

        # Sauvegarde la réponse
        await conversation_service.add_message(user_id, "assistant", assistant_reply)
        
        return assistant_reply
    except Exception as e:
        logger.error(f"Error in ask_coach_response: {e}")
        return "Je suis désolé, j'ai rencontré un problème."

async def propose_regime_intermittent(user_id: str, user_text: str, user_details: dict) -> str:
    """
    Propose un régime intermittent personnalisé.
    
    Args:
        user_id: ID de l'utilisateur
        user_text: Message de l'utilisateur
        user_details: Détails du profil utilisateur
        
    Returns:
        Plan de régime proposé
    """
    try:
        # Ajoute le message de l'utilisateur à l'historique
        await conversation_service.add_message(user_id, "user", user_text)
        
        # Prépare le message avec les détails utilisateur
        detail_str = json.dumps(user_details, ensure_ascii=False)
        profile_message = f"Voici mon profil: {detail_str}. Peux-tu me proposer un régime intermittent adapté ?"
        
        # Récupère l'historique récent
        recent_messages = await conversation_service.get_recent_messages(user_id, limit=5)
        messages_for_api = [{"role": msg.role, "content": msg.content} for msg in recent_messages]
        messages_for_api.append({"role": "user", "content": profile_message})

        # Génère le plan
        plan_text = await _call_deepseek(
            system_prompt=COACH_PROMPT,
            user_messages=messages_for_api,
            max_tokens=400
        )

        # Sauvegarde la réponse
        await conversation_service.add_message(user_id, "assistant", plan_text)
        
        return plan_text
    except Exception as e:
        logger.error(f"Error in propose_regime_intermittent: {e}")
        return "Je suis désolé, je n'arrive pas à proposer un plan maintenant."