# openai_agent.py

import os
import logging
from typing import Dict, List
import openai
from dotenv import load_dotenv

from database import update_user_summary

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY", "")
logger = logging.getLogger(__name__)

########################
# In-memory data
########################
CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}
PLANS: Dict[str, Dict] = {}
# Example of PLANS[user_id] = {
#   "questions": [ "Q1", "Q2", ... ],
#   "index": 0
# }

########################
# System prompts
########################
INITIAL_SYSTEM_PROMPT = """
You are a friendly, human-like coach. The user just wrote something in an unknown language.
1) Figure out which language they're using.
2) Respond briefly IN THAT LANGUAGE with a warm greeting, then politely ask them to confirm or specify which language they'd like to use for the rest of the conversation.
3) Keep it short.
4) Do not mention that you are analyzing their language; just do it naturally.
"""

AREAS_SYSTEM_PROMPT = """
You are a translator or copywriter. Produce a very short bullet-list message in the user's chosen language
that says something like:

"Which areas would you like to focus on? You can choose multiple:
- Personal Development
- Health & Wellness
- Professional Growth
- Relationships & Social
- Lifestyle

Which ones interest you the most?"

Keep it short, under 50 words if possible. 
Just return the final text in the correct language, no other explanation.
"""

PLAN_SYSTEM_PROMPT = """
You are a life coach. The user wants to focus on certain areas. 
Generate exactly 5 short coaching questions in the user's language. 
They should be direct, simple, and help you understand the user's goals, motivations, and obstacles. 
Return them as a bullet list, no extra text.
"""

MAIN_SYSTEM_PROMPT = """
You are a friendly, human-like coach having a normal conversation in the user's language. 
Ask clarifying questions, keep context, do not reveal you are an AI. 
Keep messages fairly short, but natural.
"""

########################
# Internal Helpers
########################
def _add_msg(user_id: str, role: str, content: str):
    """Store a single message (role=user/assistant) in memory."""
    if user_id not in CONVERSATIONS:
        CONVERSATIONS[user_id] = []
    CONVERSATIONS[user_id].append({"role": role, "content": content})

def _recent_msgs(user_id: str, limit: int = 5) -> List[Dict[str, str]]:
    """Return up to `limit` most recent messages for the user."""
    if user_id not in CONVERSATIONS:
        return []
    return CONVERSATIONS[user_id][-limit:]

def _summary_from_convo(messages: List[Dict[str, str]]) -> str:
    """Naive summary: join last 3 user messages with ' | '."""
    user_texts = [m["content"] for m in messages if m["role"] == "user"]
    last3 = user_texts[-3:]
    return " | ".join(last3)

def _call_gpt(system_prompt: str, user_messages: List[Dict[str, str]], temperature=0.7, max_tokens=200):
    """Generic helper to call GPT with a system prompt plus user messages."""
    messages_for_gpt = [{"role": "system", "content": system_prompt}] + user_messages
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages_for_gpt,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message["content"]

########################
# 1) ask_openai_first_response
########################
def ask_openai_first_response(user_id: str, user_text: str) -> str:
    """
    The first user message. We detect their language, respond in that language, 
    ask them to confirm which language to continue in. Keep it short.
    """
    try:
        # store user message
        _add_msg(user_id, "user", user_text)
        # system + user context
        chat_input = [{"role": "user", "content": user_text}]
        assistant_text = _call_gpt(INITIAL_SYSTEM_PROMPT, chat_input)

        # store assistant
        _add_msg(user_id, "assistant", assistant_text)

        # update summary
        summary = _summary_from_convo(CONVERSATIONS[user_id])
        update_user_summary(user_id, {"summary": summary})

        return assistant_text

    except Exception as e:
        logger.error(f"Error in ask_openai_first_response for {user_id}: {e}")
        return "Sorry, something went wrong."

########################
# 2) get_areas_message_in_language
########################
def get_areas_message_in_language(user_language: str) -> str:
    """
    Calls GPT with AREAS_SYSTEM_PROMPT to produce the bullet-list text 
    in the user's chosen language. 
    We'll pass user_language as a role='user' content for context.
    """
    try:
        chat_input = [{"role": "user", "content": f"Language: {user_language}"}]
        output = _call_gpt(AREAS_SYSTEM_PROMPT, chat_input, temperature=0.3, max_tokens=100)
        return output
    except Exception as e:
        logger.error(f"Error getting areas message for {user_language}: {e}")
        # fallback
        return ("Which areas do you want to focus on?\n\n"
                "- Personal Development\n- Health & Wellness\n- Professional Growth\n- Relationships\n- Lifestyle\n\n")

########################
# 3) generate_plan_for_areas
########################
def generate_plan_for_areas(user_id: str, user_language: str, user_areas: str):
    """
    Calls GPT to produce exactly 5 short coaching questions in user_language 
    based on the user's chosen areas. 
    Store them in PLANS[user_id] with index=0.
    """
    try:
        user_content = (f"User language: {user_language}\n"
                        f"User areas: {user_areas}\n")
        chat_input = [{"role": "user", "content": user_content}]
        plan_text = _call_gpt(PLAN_SYSTEM_PROMPT, chat_input, temperature=0.5, max_tokens=200)

        # plan_text is presumably bullet points, let's split them
        # We'll just do a naive split by newline if there are bullet points:
        lines = plan_text.strip().split("\n")
        questions = []
        for line in lines:
            # remove bullet chars and strip
            line_clean = line.replace("-", "").replace("*", "").replace("•", "").strip()
            if line_clean:
                questions.append(line_clean)

        # store in PLANS
        PLANS[user_id] = {
            "questions": questions,
            "index": 0
        }
    except Exception as e:
        logger.error(f"Error generating plan for user {user_id}: {e}")
        PLANS[user_id] = {
            "questions": [
                "What motivates you about these areas?",
                "How do you see your life changing if you succeed?",
                "What obstacles might stand in your way?",
                "How will you measure progress?",
                "Who can support you in this journey?"
            ],
            "index": 0
        }

########################
# 4) ask_openai_normal
########################
def ask_openai_normal(user_id: str, user_text: str) -> str:
    """
    Normal conversation once we are done with the plan or in free-form. 
    We just keep using MAIN_SYSTEM_PROMPT + last few messages.
    """
    try:
        _add_msg(user_id, "user", user_text)
        recent = _recent_msgs(user_id, limit=5)
        assistant_text = _call_gpt(MAIN_SYSTEM_PROMPT, recent, temperature=0.7, max_tokens=200)

        _add_msg(user_id, "assistant", assistant_text)
        summary = _summary_from_convo(CONVERSATIONS[user_id])
        update_user_summary(user_id, {"summary": summary})
        return assistant_text
    except Exception as e:
        logger.error(f"Error in ask_openai_normal for {user_id}: {e}")
        return "Sorry, I had an issue answering."
