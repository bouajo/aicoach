import os
import logging
from typing import Dict, List, Any
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI

from data.database import get_user, update_user_summary

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize DeepSeek client
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

########################
# In-memory data
########################
CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}

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
        return "Désolé, j’ai rencontré un problème en générant la réponse."

def _add_msg(user_id: str, role: str, content: str):
    if user_id not in CONVERSATIONS:
        CONVERSATIONS[user_id] = []
    CONVERSATIONS[user_id].append({"role": role, "content": content})

def _recent_msgs(user_id: str, limit: int = 5) -> List[Dict[str, str]]:
    if user_id not in CONVERSATIONS:
        return []
    return CONVERSATIONS[user_id][-limit:]

def _summary_from_convo(messages: List[Dict[str, str]]) -> str:
    user_texts = [m["content"] for m in messages if m["role"] == "user"]
    last3 = user_texts[-3:]
    return " | ".join(last3)

def update_user_conversation_summary(user_id: str):
    recent_messages = CONVERSATIONS.get(user_id, [])
    summary = _summary_from_convo(recent_messages)
    update_user_summary(user_id, {"summary": summary})

########################
# Main Functions
########################

async def ask_coach_response(user_id: str, user_text: str) -> str:
    try:
        _add_msg(user_id, "user", user_text)
        recent_messages = _recent_msgs(user_id, limit=5)

        assistant_reply = await _call_deepseek(
            system_prompt=COACH_PROMPT,
            user_messages=recent_messages
        )

        _add_msg(user_id, "assistant", assistant_reply)
        update_user_conversation_summary(user_id)
        return assistant_reply
    except Exception as e:
        logger.error(f"Error in ask_coach_response: {e}")
        return "Je suis désolé, j'ai rencontré un problème."

async def propose_regime_intermittent(user_id: str, user_text: str, user_details: dict) -> str:
    try:
        _add_msg(user_id, "user", user_text)
        detail_str = json.dumps(user_details, ensure_ascii=False)
        user_messages = _recent_msgs(user_id, limit=5)
        user_messages.append({
            "role": "user",
            "content": f"Voici mon profil: {detail_str}. Peux-tu me proposer un régime intermittent adapté ?"
        })

        plan_text = await _call_deepseek(
            system_prompt=COACH_PROMPT,
            user_messages=user_messages,
            max_tokens=400
        )

        _add_msg(user_id, "assistant", plan_text)
        update_user_conversation_summary(user_id)
        return plan_text
    except Exception as e:
        logger.error(f"Error in propose_regime_intermittent: {e}")
        return "Je suis désolé, je n'arrive pas à proposer un plan maintenant."