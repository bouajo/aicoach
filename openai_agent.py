# openai_agent.py

import os
import logging
from typing import Dict, List
import openai
import json
from dotenv import load_dotenv

from database import get_user, update_user_summary

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY", "")
logger = logging.getLogger(__name__)

########################
# In-memory data
########################
CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}
PLANS: Dict[str, Dict] = {}
# Example usage for additional phases:
# PLANS[user_id] = {
#     "discovery_index": 0,
#     "discovery_questions": [ ... ],
#     "plan_index": 0,
#     "plan_steps": [ ... ],
#     ...
# }

########################
# System Prompts
########################

# 1) Prompt for the very first user message to detect language
INITIAL_SYSTEM_PROMPT = """
You are a friendly, human-like diet and nutrition coach. The user just wrote their first message.

1) Detect which language they're using (French or English).
2) Respond IN THE SAME LANGUAGE with:
   - A warm greeting
   - A brief mention that you're a diet/nutrition coach
   - Ask them to confirm if they want to continue in French or English

Keep it natural and friendly. Don't mention that you're detecting their language.

Example if they write in French:
"Bonjour ! Je suis votre coach en nutrition. Souhaitez-vous que nous continuions en français ou en anglais ?"

Example if they write in English:
"Hello! I'm your nutrition coach. Would you like us to continue in French or English?"
"""

# 2) Prompt to ask the user about which areas they'd like to focus on
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

# 3) Prompt for generating a simple 5-question plan
PLAN_SYSTEM_PROMPT = """
You are a life coach. The user wants to focus on certain areas. 
Generate exactly 5 short coaching questions in the user's language. 
They should be direct, simple, and help you understand the user's goals, motivations, and obstacles. 
Return them as a bullet list, no extra text.
"""

# 4) Main prompt for the "active" state (short messages, empathetic, Step 2)
MAIN_SYSTEM_PROMPT = """
You are a friendly, empathetic life coach that references the user's past statements, details, and context, which are summarized here:

CONVERSATION SUMMARY: {summary}

Your style is warm, supportive, and personal. You must always respond in {user_language}, keeping your messages fairly short.
You want to learn more about the user as a person: their age, background, daily life, environment, challenges, and aspirations.
Ask follow-up questions naturally and show genuine curiosity, but do not reveal you are an AI or mention the 'summary'.

If you lack specific information about the user, politely ask clarifying questions to gather more details about their life situation.
"""

# ---------------- NEW PROMPTS FOR DEEPER DISCOVERY & MULTI-HORIZON PLANNING ----------------

# A) Discovery Prompt: Gather personal info (age, gender, daily routine, etc.)
DISCOVERY_SYSTEM_PROMPT = """
You are a thorough life coach who wants to learn about the user's personal background to better guide them.
You must always speak in {user_language}, keep your messages short, and ask relevant follow-up questions
about the user's demographics (age, gender), daily environment (city, family situation, routine), and personal interests.

Do not mention that you are an AI or using a 'prompt'. Speak in a friendly, empathetic manner.
"""

# B) Multi-Horizon Planning Prompt: Short-, medium-, and long-term steps
PLANNING_SYSTEM_PROMPT = """
You are a methodical life coach who, given the user's personal details and goals, will propose a structured plan
covering short-term (next few weeks), medium-term (next few months), and long-term (beyond 6 months) steps.
All responses must be in {user_language}, concise, and broken into clear steps or milestones.
You can refer to the user's objectives, constraints, and motivations. Keep it supportive and practical.
Do not reveal you are an AI or mention any 'summary' or 'prompt'.
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
    """
    Naive summary: join the last 3 user messages with ' | '.
    Helps keep track of key points from recent user inputs.
    """
    user_texts = [m["content"] for m in messages if m["role"] == "user"]
    last3 = user_texts[-3:]
    return " | ".join(last3)

async def _call_gpt(system_prompt: str, user_messages: List[Dict[str, str]], temperature=0.7, max_tokens=200):
    """Generic helper to call GPT with a system prompt plus user messages."""
    messages_for_gpt = [{"role": "system", "content": system_prompt}] + user_messages
    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=messages_for_gpt,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message["content"]

########################
# Existing Functions for Different Steps
########################

async def ask_openai_first_response(user_id: str, user_text: str) -> str:
    """
    The first user message. Detect language, respond in that language, 
    ask for confirmation. Keep it short.
    """
    try:
        _add_msg(user_id, "user", user_text)
        chat_input = [{"role": "user", "content": user_text}]
        assistant_text = await _call_gpt(INITIAL_SYSTEM_PROMPT, chat_input)

        _add_msg(user_id, "assistant", assistant_text)

        # Update summary in the DB
        summary = _summary_from_convo(CONVERSATIONS[user_id])
        update_user_summary(user_id, {"summary": summary})

        return assistant_text

    except Exception as e:
        logger.error(f"Error in ask_openai_first_response for {user_id}: {e}")
        return "Sorry, something went wrong."

async def get_areas_message_in_language(user_language: str) -> str:
    """
    Calls GPT with AREAS_SYSTEM_PROMPT to produce the bullet-list text in the user's chosen language.
    """
    try:
        chat_input = [{"role": "user", "content": f"Language: {user_language}"}]
        output = await _call_gpt(
            AREAS_SYSTEM_PROMPT,
            chat_input,
            temperature=0.3,
            max_tokens=100
        )
        return output
    except Exception as e:
        logger.error(f"Error getting areas message for {user_language}: {e}")
        return (
            "Which areas do you want to focus on?\n"
            "- Personal Development\n- Health & Wellness\n- Professional Growth\n- Relationships\n- Lifestyle\n"
        )

async def generate_plan_for_areas(user_id: str, user_language: str, user_areas: str):
    """
    Calls GPT to produce exactly 5 short coaching questions in user_language 
    based on the user's chosen areas. 
    Stores them in PLANS[user_id] with index=0, for step-by-step questioning.
    """
    try:
        user_content = f"User language: {user_language}\nUser areas: {user_areas}\n"
        chat_input = [{"role": "user", "content": user_content}]
        plan_text = await _call_gpt(PLAN_SYSTEM_PROMPT, chat_input, temperature=0.5, max_tokens=200)

        # Naive split by newline for bullet points
        lines = plan_text.strip().split("\n")
        questions = []
        for line in lines:
            # remove bullet chars and strip
            line_clean = line.replace("-", "").replace("*", "").replace("•", "").strip()
            if line_clean:
                questions.append(line_clean)

        PLANS[user_id] = {
            "questions": questions,
            "index": 0
        }
    except Exception as e:
        logger.error(f"Error generating plan for user {user_id}: {e}")
        # fallback plan
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

async def ask_openai_normal(user_id: str, user_text: str) -> str:
    """
    Normal conversation (state='active'). 
    Uses MAIN_SYSTEM_PROMPT with the user's summary and language.
    """
    try:
        _add_msg(user_id, "user", user_text)
        recent_messages = _recent_msgs(user_id, limit=5)

        user_record = get_user(user_id) or {}
        user_summary = user_record.get("conversation_summary", {}).get("summary", "")
        user_language = user_record.get("language", "français")

        system_prompt = MAIN_SYSTEM_PROMPT.format(
            summary=user_summary,
            user_language=user_language
        )

        assistant_text = await _call_gpt(
            system_prompt,
            recent_messages,
            temperature=0.7,
            max_tokens=100  # shorter replies
        )

        _add_msg(user_id, "assistant", assistant_text)

        updated_summary = _summary_from_convo(CONVERSATIONS[user_id])
        update_user_summary(user_id, {"summary": updated_summary})

        return assistant_text

    except Exception as e:
        logger.error(f"Error in ask_openai_normal for {user_id}: {e}")
        return "Sorry, I had an issue answering."

########################
# New Functions for Enhanced Discovery & Planning
########################

async def ask_openai_discovery(user_id: str, user_text: str) -> str:
    """
    Life-focused discovery conversation to understand the person's journey.
    """
    try:
        _add_msg(user_id, "user", user_text)
        recent_messages = _recent_msgs(user_id, limit=5)

        # Get user record and parse details
        user_record = get_user(user_id) or {}
        user_language = user_record.get("language", "français")
        
        # Parse new details from the current message
        try:
            new_details = await parse_user_details_from_text(user_id, user_text)
        except Exception as e:
            logger.error(f"Error parsing details in discovery: {e}")
            new_details = {}
        
        # Merge with existing details from user record
        existing_details = user_record.get("user_details", {})
        merged_details = {**existing_details, **new_details}
        
        # Format the discovery prompt with user details
        system_prompt = DISCOVERY_SYSTEM_PROMPT.format(
            user_language=user_language,
            life_vision=merged_details.get("life_vision", "exploring life direction"),
            age=merged_details.get("age", "unknown"),
            current_situation=merged_details.get("current_situation", "unknown"),
            challenges=", ".join(merged_details.get("challenges", []))
        )

        assistant_text = await _call_gpt(
            system_prompt,
            recent_messages,
            temperature=0.7,
            max_tokens=120
        )

        _add_msg(user_id, "assistant", assistant_text)

        # Update user details and summary in the DB
        updated_summary = _summary_from_convo(CONVERSATIONS[user_id])
        update_user_summary(user_id, {
            "summary": updated_summary,
            "user_details": merged_details
        })

        return assistant_text

    except Exception as e:
        logger.error(f"Error in ask_openai_discovery for {user_id}: {e}")
        return "I'd love to understand more about your life journey. Could you tell me what brings you here today?"

async def generate_multi_horizon_plan(user_id: str, user_goals: str) -> str:
    """
    Creates a short-, medium-, and long-term plan based on the user's goals 
    and personal details.
    """
    try:
        user_record = get_user(user_id) or {}
        user_language = user_record.get("language", "français")

        # Build user content with goals and possibly existing summary
        user_content = f"User language: {user_language}\nUser goals: {user_goals}\n"
        summary = user_record.get("conversation_summary", {}).get("summary", "")
        if summary:
            user_content += f"Additional user context: {summary}\n"

        chat_input = [{"role": "user", "content": user_content}]

        system_prompt = PLANNING_SYSTEM_PROMPT.format(user_language=user_language)

        plan_text = await _call_gpt(
            system_prompt,
            chat_input,
            temperature=0.7,
            max_tokens=300
        )

        return plan_text

    except Exception as e:
        logger.error(f"Error generating multi-horizon plan for user {user_id}: {e}")
        return ("I'm sorry, I had trouble generating a detailed plan right now. "
                "Please try again later or provide more details.")

async def parse_user_details_from_text(user_id: str, user_text: str) -> dict:
    """
    Call GPT to parse user_text for personal details.
    Returns a dictionary with extracted information.
    """
    try:
        system_prompt = """
You are an information extraction engine. The user wrote the text below.
Extract any personal details such as age, gender, location, daily routine, personal interests, or other relevant info.
Return a JSON object with exactly these fields: "age", "gender", "location", "routine", "interests", "other".
If any field is not mentioned by the user, use an empty string or a short description.

ONLY return valid JSON. Do not include any extra text or explanation.
"""
        user_message = [{"role": "user", "content": user_text}]
        
        gpt_response = await _call_gpt(
            system_prompt=system_prompt,
            user_messages=user_message,
            temperature=0.3,
            max_tokens=200
        )
        
        details_dict = json.loads(gpt_response)
        
        # Make sure it has the expected keys
        for key in ["age", "gender", "location", "routine", "interests", "other"]:
            if key not in details_dict:
                details_dict[key] = ""
        
        return details_dict

    except Exception as e:
        logger.error(f"Error parsing user details for {user_id}: {e}")
        return {
            "age": "",
            "gender": "",
            "location": "",
            "routine": "",
            "interests": "",
            "other": ""
        }

async def ask_openai_normal(user_id: str, user_text: str) -> str:
    """
    Enhanced life coaching conversation with holistic context awareness.
    """
    try:
        _add_msg(user_id, "user", user_text)
        recent_messages = _recent_msgs(user_id, limit=5)

        user_record = get_user(user_id) or {}
        user_summary = user_record.get("conversation_summary", {}).get("summary", "")
        user_language = user_record.get("language", "français")  # Changed default to français
        user_details = user_record.get("user_details", {})

        # Parse any new details from user's message
        try:
            new_details = await parse_user_details_from_text(user_id, user_text)
            if any(new_details.values()):
                merged_details = {**user_details, **new_details}
                user_details = merged_details
        except Exception as e:
            logger.error(f"Error parsing details in normal conversation: {e}")

        # Format the main prompt with all user details
        system_prompt = MAIN_SYSTEM_PROMPT.format(
            age=user_details.get("age", "unknown"),
            life_stage=user_details.get("life_stage", "unknown"),
            location=user_details.get("location", "unknown"),
            life_vision=user_details.get("life_vision", "exploring life direction"),
            challenges=", ".join(user_details.get("challenges", [])),
            current_situation=user_details.get("current_situation", "not specified"),
            aspirations=", ".join(user_details.get("aspirations", [])),
            summary=user_summary,
            user_language=user_language
        )

        assistant_text = await _call_gpt(
            system_prompt,
            recent_messages,
            temperature=0.7,
            max_tokens=100
        )

        _add_msg(user_id, "assistant", assistant_text)

        # Update the database with new details if we have them
        updated_summary = _summary_from_convo(CONVERSATIONS[user_id])
        update_user_summary(user_id, {
            "summary": updated_summary,
            "user_details": user_details
        })

        return assistant_text

    except Exception as e:
        logger.error(f"Error in ask_openai_normal for {user_id}: {e}")
        return "Could you share more about what's on your mind? I'm here to listen and help you explore your thoughts."

async def analyze_language_choice(user_id: str, user_text: str) -> tuple[str, str]:
    """
    Analyzes the user's language choice response and returns a tuple of (language_code, confirmation_message).
    Uses GPT to understand the intent even if the user doesn't use exact keywords.
    """
    try:
        system_prompt = """
You are analyzing a user's response to choose between French and English.
Detect their language preference regardless of how they express it.
Return a JSON object with exactly two fields:
{
    "language": "français" or "english",
    "confirmation_message": "confirmation message in their chosen language"
}

Examples of analysis:
"Je préfère le français" -> {"language": "français", "confirmation_message": "Parfait, nous allons continuer en français..."}
"English please" -> {"language": "english", "confirmation_message": "Perfect, we'll continue in English..."}
"French" -> {"language": "français", "confirmation_message": "Parfait, nous allons continuer en français..."}
"Anglais" -> {"language": "english", "confirmation_message": "Perfect, we'll continue in English..."}

If the choice is unclear, set language to "unknown" and provide a bilingual message asking for clarification.
"""
        chat_input = [{"role": "user", "content": user_text}]
        response = await _call_gpt(
            system_prompt,
            chat_input,
            temperature=0.3,
            max_tokens=150
        )
        
        result = json.loads(response)
        return result["language"], result["confirmation_message"]

    except Exception as e:
        logger.error(f"Error analyzing language choice for {user_id}: {e}")
        return "unknown", (
            "Je n'ai pas compris votre choix de langue. Pourriez-vous répondre simplement 'Français' ou 'English' ?\n"
            "I didn't understand your language choice. Could you simply reply with 'Français' or 'English'?"
        ) 
