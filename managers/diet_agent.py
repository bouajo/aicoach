"""
Manages a single AI Agent (Eric) for diet-related interactions.
This agent:
1. Detects or confirms the user's preferred language.
2. Collects all necessary information (name, age, weights, etc.) step by step.
3. Proposes a personalized diet plan using historical conversation context.
4. Tracks progress over time, celebrates milestones, and updates the plan.
Nothing is hard-coded about the user or their data; everything is filled dynamically.
"""

from typing import Dict, Any, Optional

# The base instructions for Eric: the AI must handle all conversation stages
BASE_AGENT_PROMPT = """
You are "Eric", an AI specialized in personalized diet and wellness coaching.
Your conversation has multiple potential steps:
1) **Language Check**: If the user's language is unknown, politely detect or confirm it. Then respond in that language going forward.
2) **Data Collection**: Collect any missing user info (name, age, height, start weight, target weight, target date, diet preferences, restrictions). Ask for ONE piece of data at a time to avoid overwhelming them.
3) **Plan Proposal**: Once enough data is known, propose a personalized plan. Summarize the plan clearly (meals, habits, weekly or monthly goals). Use conversation history to recall user details or preferences.
4) **Progress Tracking & Milestones**: Track changes in user’s weight or timeline, celebrate small wins, adjust the plan as needed. Provide key milestones (weekly or monthly check-ins) for the user to follow.

=== Key Principles ===
- Always be empathetic and occasionally humorous. Make short, tasteful jokes.
- Do NOT give medical diagnoses; clarify you are an AI assistant, not a doctor.
- Keep everything user-centric and supportive.
- If the user expresses frustration or obstacles, respond with empathy and constructive tips.
- If crucial info is still missing, gently prompt the user for it.
- Summaries or references to past conversation are crucial for continuity.

=== User Data & Context ===
{USER_DATA}

=== Guidelines ===
- Respond **exclusively** in the user's preferred language (if known). If unknown, try to detect it or ask them politely.
- If missing fields exist, gather them step by step.
- Provide a plan or advice only once enough data is known.
- Show gentle humor and positivity.
- Keep solutions realistic (healthy weight loss of 0.5-1 kg/week recommended, etc.).
- Provide or refine timeline with user’s target date if available.

=== Conversation History Summary ===
{CONVERSATION_SUMMARY}

Given all of the above, produce the best possible answer to the user's latest message.
"""


def build_diet_agent_prompt(
    user_profile: Dict[str, Any],
    conversation_summary: str,
    user_language: Optional[str] = None
) -> str:
    """
    Constructs the single system prompt for Eric by injecting:
      - user profile data
      - conversation summary
      - user language (if detected)

    Args:
        user_profile (dict): The user's profile from the DB (may be partially filled).
        conversation_summary (str): Summarized conversation so far.
        user_language (str): If we've already detected or stored the user's language, pass it here.

    Returns:
        str: A fully populated system prompt for the AI Agent (Eric).
    """

    # Build up a text blob with all known user data
    # (Use the keys from your DB schema as relevant)
    user_name = user_profile.get("first_name", "")
    age = user_profile.get("age", "")
    height_cm = user_profile.get("height_cm", "")
    start_weight = user_profile.get("start_weight", "")
    current_weight = user_profile.get("current_weight", "")
    target_weight = user_profile.get("target_weight", "")
    target_date = user_profile.get("target_date", "")
    diet_prefs = user_profile.get("diet_preferences", [])
    diet_restrictions = user_profile.get("diet_restrictions", [])

    # Check if we have a known language or not
    # If none is stored, the AI is expected to figure it out or ask
    final_language = user_language if user_language else user_profile.get("language", "undetected")

    # Format the user data portion
    user_data_text = f"""
Name: {user_name if user_name else 'Unknown'}
Age: {age if age else 'Unknown'}
Height (cm): {height_cm if height_cm else 'Unknown'}
Start Weight (kg): {start_weight if start_weight else 'Unknown'}
Current Weight (kg): {current_weight if current_weight else 'Unknown'}
Target Weight (kg): {target_weight if target_weight else 'Unknown'}
Target Date: {target_date if target_date else 'Unknown'}
Diet Preferences: {", ".join(diet_prefs) if diet_prefs else "None specified"}
Diet Restrictions: {", ".join(diet_restrictions) if diet_restrictions else "None specified"}
Preferred Language (if known): {final_language}
"""

    # Merge it all into the base prompt
    system_prompt = BASE_AGENT_PROMPT.replace("{USER_DATA}", user_data_text.strip())
    system_prompt = system_prompt.replace("{CONVERSATION_SUMMARY}", conversation_summary or "No prior summary.")

    return system_prompt
