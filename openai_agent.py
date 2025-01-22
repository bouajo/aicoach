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
You are a friendly, human-like coach. The user just wrote something in an unknown language.
1) Figure out which language they're using.
2) Respond briefly IN THAT LANGUAGE with a warm greeting, then politely ask them to confirm or specify which language they'd like to use for the rest of the conversation.
3) Keep it short.
4) Do not mention that you are analyzing their language; just do it naturally.
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
# Existing Functions for Different Steps
########################

def ask_openai_first_response(user_id: str, user_text: str) -> str:
    """
    The first user message. Detect language, respond in that language, 
    ask for confirmation. Keep it short.
    """
    try:
        _add_msg(user_id, "user", user_text)
        chat_input = [{"role": "user", "content": user_text}]
        assistant_text = _call_gpt(INITIAL_SYSTEM_PROMPT, chat_input)

        _add_msg(user_id, "assistant", assistant_text)

        # Update summary in the DB
        summary = _summary_from_convo(CONVERSATIONS[user_id])
        update_user_summary(user_id, {"summary": summary})

        return assistant_text

    except Exception as e:
        logger.error(f"Error in ask_openai_first_response for {user_id}: {e}")
        return "Sorry, something went wrong."

def get_areas_message_in_language(user_language: str) -> str:
    """
    Calls GPT with AREAS_SYSTEM_PROMPT to produce the bullet-list text in the user's chosen language.
    """
    try:
        chat_input = [{"role": "user", "content": f"Language: {user_language}"}]
        output = _call_gpt(
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

def generate_plan_for_areas(user_id: str, user_language: str, user_areas: str):
    """
    Calls GPT to produce exactly 5 short coaching questions in user_language 
    based on the user's chosen areas. 
    Stores them in PLANS[user_id] with index=0, for step-by-step questioning.
    """
    try:
        user_content = f"User language: {user_language}\nUser areas: {user_areas}\n"
        chat_input = [{"role": "user", "content": user_content}]
        plan_text = _call_gpt(PLAN_SYSTEM_PROMPT, chat_input, temperature=0.5, max_tokens=200)

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

def ask_openai_normal(user_id: str, user_text: str) -> str:
    """
    Normal conversation (state='active'). 
    Uses MAIN_SYSTEM_PROMPT with the user's summary and language.
    """
    try:
        _add_msg(user_id, "user", user_text)
        recent_messages = _recent_msgs(user_id, limit=5)

        user_record = get_user(user_id) or {}
        user_summary = user_record.get("conversation_summary", {}).get("summary", "")
        user_language = user_record.get("language", "English")

        system_prompt = MAIN_SYSTEM_PROMPT.format(
            summary=user_summary,
            user_language=user_language
        )

        assistant_text = _call_gpt(
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

def ask_openai_discovery(user_id: str, user_text: str) -> str:
    """
    A "discovery" conversation step to gather deeper personal info:
    e.g., age, background, daily routine, environment, etc.
    """
    try:
        _add_msg(user_id, "user", user_text)
        recent_messages = _recent_msgs(user_id, limit=5)

        user_record = get_user(user_id) or {}
        user_summary = user_record.get("conversation_summary", {}).get("summary", "")
        user_language = user_record.get("language", "English")

        # Format the discovery prompt
        system_prompt = DISCOVERY_SYSTEM_PROMPT.format(user_language=user_language)

        assistant_text = _call_gpt(
            system_prompt,
            recent_messages,
            temperature=0.7,
            max_tokens=120
        )

        _add_msg(user_id, "assistant", assistant_text)

        # Update the summary in the DB
        updated_summary = _summary_from_convo(CONVERSATIONS[user_id])
        update_user_summary(user_id, {"summary": updated_summary})

        return assistant_text

    except Exception as e:
        logger.error(f"Error in ask_openai_discovery for {user_id}: {e}")
        return "Sorry, something went wrong while discovering more about you."

def generate_multi_horizon_plan(user_id: str, user_goals: str) -> str:
    """
    Creates a short-, medium-, and long-term plan based on the user's goals 
    and personal details.
    """
    try:
        user_record = get_user(user_id) or {}
        user_language = user_record.get("language", "English")

        # Build user content with goals and possibly existing summary
        user_content = f"User language: {user_language}\nUser goals: {user_goals}\n"
        summary = user_record.get("conversation_summary", {}).get("summary", "")
        if summary:
            user_content += f"Additional user context: {summary}\n"

        chat_input = [{"role": "user", "content": user_content}]

        system_prompt = PLANNING_SYSTEM_PROMPT.format(user_language=user_language)

        plan_text = _call_gpt(
            system_prompt,
            chat_input,
            temperature=0.7,
            max_tokens=300
        )

        # Optionally store this text in your DB or in PLANS[user_id]
        return plan_text

    except Exception as e:
        logger.error(f"Error generating multi-horizon plan for user {user_id}: {e}")
        return ("I'm sorry, I had trouble generating a detailed plan right now. "
                "Please try again later or provide more details.")
    
import json

def parse_user_details_from_text(user_id: str, user_text: str) -> dict:
    """
    Call GPT to parse user_text for personal details like age, location, gender, routine, etc.
    Returns a dictionary with keys: "age", "gender", "location", "routine", "interests", "other".
    If nothing is found, the values can be empty strings.
    """
    try:
        # We create a system prompt to instruct GPT to ONLY return valid JSON
        system_prompt = """
You are an information extraction engine. The user wrote the text below.
Extract any personal details such as age, gender, location, daily routine, personal interests, or other relevant info.
Return a JSON object with exactly these fields: "age", "gender", "location", "routine", "interests", "other".
If any field is not mentioned by the user, use an empty string or a short description.

ONLY return valid JSON. Do not include any extra text or explanation.
"""

        # We'll treat user_text as the 'user' message
        user_message = [{"role": "user", "content": user_text}]

        # Call GPT with a tight max_tokens
        gpt_response = _call_gpt(
            system_prompt=system_prompt,
            user_messages=user_message,
            temperature=0.3,
            max_tokens=200
        )
        
        # Attempt to parse JSON
        details_dict = json.loads(gpt_response)
        
        # Make sure it has the expected keys
        for key in ["age", "gender", "location", "routine", "interests", "other"]:
            if key not in details_dict:
                details_dict[key] = ""
        
        return details_dict

    except Exception as e:
        logger.error(f"Error parsing user details for {user_id}: {e}")
        # Return empty structure if there's a problem
        return {
            "age": "",
            "gender": "",
            "location": "",
            "routine": "",
            "interests": "",
            "other": ""
        }
# Discovery Prompt: Life coaching focus
DISCOVERY_SYSTEM_PROMPT = """
You are an empathetic life coach who helps people understand their life goals and aspirations.
You must always speak in {user_language} and keep your messages conversational.

Current context about the user:
- Life Vision: {life_vision}
- Age: {age}
- Current Situation: {current_situation}
- Key Challenges: {challenges}

Based on their life vision:
1. If seeking purpose: Ask about their values, passions, and what gives them meaning
2. If career growth: Explore their skills, interests, and ideal work environment
3. If personal growth: Discuss their self-development goals and learning aspirations
4. If life balance: Understand their priorities and what balance means to them

Keep your tone warm and supportive. Ask ONE thoughtful question at a time.
If you don't have some information above, explore it naturally.

Remember:
- Focus on understanding their deeper motivations
- Help them reflect on their life journey
- Keep responses under 100 words
- Ask open-ended questions that encourage self-reflection
"""

# Main Prompt: Life coaching context
MAIN_SYSTEM_PROMPT = """
You are an insightful life coach helping people navigate their life journey. Here's what you know about the person:

PERSONAL CONTEXT:
- Age: {age}
- Life Stage: {life_stage}
- Location: {location}
- Life Vision: {life_vision}
- Key Challenges: {challenges}
- Current Situation: {current_situation}
- Aspirations: {aspirations}

CONVERSATION HISTORY:
{summary}

COACHING GUIDELINES:
1. Always respond in {user_language}
2. Keep responses concise but meaningful
3. Reference their personal context when relevant
4. Show you understand their journey
5. Help them reflect on their choices and decisions
6. For purpose-seeking: Guide them to explore their values
7. For personal growth: Help them identify learning opportunities
8. For life transitions: Support them in managing change

Focus on:
- Deeper understanding of their motivations
- Identifying patterns in their life story
- Connecting their past experiences to future aspirations
- Encouraging self-reflection and awareness

Don't mention being AI or reference this context directly.
Ask thoughtful questions that promote personal insight.
"""

def parse_user_details_from_text(user_id: str, user_text: str) -> dict:
    """
    Enhanced parser to extract life-focused personal details.
    """
    try:
        system_prompt = """
You are an empathetic listener analyzing someone's life story. Extract key personal details.
If the text is in French or another language, translate the information but keep original quotes.

Return a JSON object with these fields:
{
    "age": "35",  // Extract number only, or "" if not found
    "life_stage": "", // E.g., "career transition", "starting family", "retirement"
    "location": "", // City/country if mentioned
    "current_situation": "", // Work, life circumstances, key activities
    "aspirations": [], // List of hopes, dreams, goals
    "challenges": [], // List of current difficulties or obstacles
    "life_vision": "", // Their ideal future or life direction
    "values": [] // What matters most to them
}

Examples of insight detection:
- "Je veux trouver un sens à ma vie" → life_vision: "seeking purpose and meaning"
- "I feel stuck in my career" → challenges: ["career stagnation"]
- "I dream of making a difference" → aspirations: ["creating positive impact"]

ONLY return valid JSON. No other text."""

        user_message = [{"role": "user", "content": user_text}]
        
        gpt_response = _call_gpt(
            system_prompt=system_prompt,
            user_messages=user_message,
            temperature=0.3,
            max_tokens=200
        )
        
        details_dict = json.loads(gpt_response)
        
        # Ensure all required keys exist
        required_keys = ["age", "life_stage", "location", "current_situation", "aspirations", "challenges", "life_vision", "values"]
        for key in required_keys:
            if key not in details_dict:
                details_dict[key] = "" if key not in ["aspirations", "challenges", "values"] else []
        
        return details_dict

    except Exception as e:
        logger.error(f"Error parsing user details for {user_id}: {e}")
        return {
            "age": "",
            "life_stage": "",
            "location": "",
            "current_situation": "",
            "aspirations": [],
            "challenges": [],
            "life_vision": "",
            "values": []
        }

async def ask_openai_discovery(user_id: str, user_text: str) -> str:
    """
    Life-focused discovery conversation to understand the person's journey.
    """
    try:
        _add_msg(user_id, "user", user_text)
        recent_messages = _recent_msgs(user_id, limit=5)

        # Get user record and parse details
        user_record = get_user(user_id) or {}
        user_language = user_record.get("language", "English")
        
        # Parse new details from the current message
        new_details = parse_user_details_from_text(user_id, user_text)
        
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

        assistant_text = _call_gpt(
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

async def ask_openai_normal(user_id: str, user_text: str) -> str:
    """
    Enhanced life coaching conversation with holistic context awareness.
    """
    try:
        _add_msg(user_id, "user", user_text)
        recent_messages = _recent_msgs(user_id, limit=5)

        user_record = get_user(user_id) or {}
        user_summary = user_record.get("conversation_summary", {}).get("summary", "")
        user_language = user_record.get("language", "English")
        user_details = user_record.get("user_details", {})

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

        assistant_text = _call_gpt(
            system_prompt,
            recent_messages,
            temperature=0.7,
            max_tokens=100
        )

        _add_msg(user_id, "assistant", assistant_text)

        # Parse any new details from user's message
        new_details = parse_user_details_from_text(user_id, user_text)
        
        # Update user details if new information is found
        if any(new_details.values()):
            merged_details = {**user_details, **new_details}
            updated_summary = _summary_from_convo(CONVERSATIONS[user_id])
            update_user_summary(user_id, {
                "summary": updated_summary,
                "user_details": merged_details
            })

        return assistant_text

    except Exception as e:
        logger.error(f"Error in ask_openai_normal for {user_id}: {e}")
        return "Could you share more about what's on your mind? I'm here to listen and help you explore your thoughts." 
