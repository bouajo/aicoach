import os
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv

from database import get_user, create_or_update_user
from openai_agent import (
    ask_openai_first_response,
    ask_openai_discovery,
    ask_openai_normal,
    parse_user_details_from_text,
    generate_multi_horizon_plan,
    analyze_language_choice
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER", "")

SESSION_NAME = "telegram_user_session"

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handle_incoming(event):
    if not event.is_private:
        return  # ignore group messages, handle only private chats
    
    sender = await event.get_sender()
    user_id = f"tg_{sender.id}"
    user_text = event.raw_text.strip()

    # Grab or create the user in the DB
    user_record = get_user(user_id)
    if not user_record:
        user_record = create_or_update_user(user_id, {
            "conversation_state": "init",
            "language": "",
            "conversation_summary": {},
            "user_details": {}
        })

    state = user_record.get("conversation_state", "init")
    language = user_record.get("language", "français")  # fallback
    user_details = user_record.get("user_details", {})
    
    try:
        # ----------------------------------------------------------------------
        # STATE: INIT
        # ----------------------------------------------------------------------
        if state == "init":
            # Use ask_openai_first_response to detect language and respond appropriately
            initial_reply = await ask_openai_first_response(user_id, user_text)
            
            create_or_update_user(user_id, {
                "conversation_state": "waiting_language",
                "discovery_questions": [
                    "age",
                    "current_weight",
                    "target_weight",
                    "dietary_restrictions",
                    "daily_routine"
                ],
                "discovery_index": 0
            })
            await event.respond(initial_reply)

        # ----------------------------------------------------------------------
        # STATE: WAITING_LANGUAGE
        # ----------------------------------------------------------------------
        elif state == "waiting_language":
            # Use GPT to analyze the language choice
            selected_language, confirmation = await analyze_language_choice(user_id, user_text)
            
            if selected_language == "unknown":
                await event.respond(confirmation)
                return
            
            # Store the language choice and move to discovery
            create_or_update_user(user_id, {
                "language": selected_language,
                "conversation_state": "discovery"
            })
            
            # Add the first discovery question to the confirmation
            first_question = get_next_question("age", selected_language)
            full_response = f"{confirmation}\n\n{first_question}"
            await event.respond(full_response)

        # ----------------------------------------------------------------------
        # STATE: DISCOVERY
        # ----------------------------------------------------------------------
        elif state == "discovery":
            # Get the current question index and list
            discovery_questions = user_record.get("discovery_questions", [])
            current_index = user_record.get("discovery_index", 0)
            
            # Store the answer to the current question
            if current_index < len(discovery_questions):
                current_question = discovery_questions[current_index]
                user_details[current_question] = user_text
            
            # AI coaching style for discovery and context gathering
            discovery_reply = await ask_openai_discovery(user_id, user_text)

            # Update user details with parsed information
            try:
                parsed = await parse_user_details_from_text(user_id, user_text)
                for key, val in parsed.items():
                    if val:
                        user_details[key] = val
            except Exception as e:
                logger.error(f"Error parsing user details: {e}")
                # Continue with existing user details if parsing fails

            # Save updated details and increment question index
            next_index = current_index + 1
            create_or_update_user(user_id, {
                "user_details": user_details,
                "discovery_index": next_index
            })

            # Check if we should move to coaching or ask next question
            if next_index >= len(discovery_questions):
                # Move to coaching state
                create_or_update_user(user_id, {"conversation_state": "coaching"})
                follow_up = (
                    "Merci pour toutes ces informations ! Je comprends mieux votre situation. "
                    "Parlons maintenant de votre plan personnalisé. Que pensez-vous être votre plus grand défi ?"
                ) if language.lower() == "français" else (
                    "Thank you for all this information! I better understand your situation. "
                    "Let's now talk about your personalized plan. What do you think is your biggest challenge?"
                )
            else:
                # Ask next discovery question
                next_question = discovery_questions[next_index]
                follow_up = get_next_question(next_question, language)

            # Combine AI reply with follow-up
            combined_reply = f"{discovery_reply}\n\n{follow_up}"
            await event.respond(combined_reply)

        # ----------------------------------------------------------------------
        # STATE: COACHING
        # ----------------------------------------------------------------------
        else:
            """
            Normal coaching conversation. We can also detect if the user wants a plan
            by checking if they say "plan" in the text, then call generate_multi_horizon_plan.
            """
            reply = await ask_openai_normal(user_id, user_text)
            await event.respond(reply)

            # If the user explicitly wants a plan:
            if "plan" in user_text.lower():
                user_goals = user_details.get("main_goal", "a general diet improvement")
                plan_text = generate_multi_horizon_plan(user_id, user_goals)
                await event.respond(plan_text)

    except Exception as e:
        logger.error(f"Error handling message for user {user_id}: {e}")
        await event.respond("Sorry, I encountered a problem on my end.")

async def main():
    await client.start(phone=PHONE_NUMBER)
    if not await client.is_user_authorized():
        try:
            await client.run_until_disconnected()
        except SessionPasswordNeededError:
            pwd = input("Two-step verification is enabled. Please enter your password: ")
            await client.sign_in(password=pwd)

    logger.info("Telegram user session started. Listening for messages...")
    await client.run_until_disconnected()

def get_next_question(question_key: str, language: str) -> str:
    """Helper to get the next question in the appropriate language."""
    questions = {
        "age": {
            "français": "Quel âge avez-vous ?",
            "english": "What is your age?"
        },
        "current_weight": {
            "français": "Quel est votre poids actuel ?",
            "english": "What is your current weight?"
        },
        "target_weight": {
            "français": "Quel est votre objectif de poids ?",
            "english": "What is your target weight?"
        },
        "dietary_restrictions": {
            "français": "Avez-vous des restrictions alimentaires particulières ?",
            "english": "Do you have any dietary restrictions?"
        },
        "daily_routine": {
            "français": "Pouvez-vous me décrire votre routine quotidienne ?",
            "english": "Can you describe your daily routine?"
        }
    }
    
    lang = language.lower()
    if lang not in ["français", "english"]:
        lang = "français"  # default to French
        
    return questions.get(question_key, {}).get(lang, "")

if __name__ == "__main__":
    asyncio.run(main())
