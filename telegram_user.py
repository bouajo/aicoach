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
    generate_multi_horizon_plan
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
        return  # ignore group messages

    sender = await event.get_sender()
    user_id = f"tg_{sender.id}"
    user_text = event.raw_text.strip()

    # Grab or create user from DB
    user_record = get_user(user_id)
    if not user_record:
        user_record = create_or_update_user(user_id, {
            "conversation_state": "init",
            "language": "",
            "conversation_summary": {},
            "user_details": {}  # For storing age, gender, etc.
        })

    state = user_record.get("conversation_state", "init")
    language = user_record.get("language", "français")  # fallback
    user_details = user_record.get("user_details", {})
    # We'll store whether user wants weight loss, relationships, or something else in user_details["main_goal"].

    try:
        # -----------------------------------------
        # STATE: INIT
        # -----------------------------------------
        if state == "init":
            # Greet and ask which language
            reply = ask_openai_first_response(user_id, user_text)
            create_or_update_user(user_id, {"conversation_state": "waiting_language"})
            await event.respond(reply)

        # -----------------------------------------
        # STATE: WAITING_LANGUAGE
        # -----------------------------------------
        elif state == "waiting_language":
            # Store user language, move to discovery
            create_or_update_user(user_id, {
                "language": user_text.lower(),
                "conversation_state": "discovery"
            })
            await event.respond(
                f"Parfait, nous allons continuer en {user_text}. Parlez-moi un peu de votre objectif principal ou situation actuelle."
            )

        # -----------------------------------------
        # STATE: DISCOVERY
        # -----------------------------------------
        elif state == "discovery":
            """
            In 'discovery', we gather more context about the user:
              - If they specify a main goal (e.g., losing weight), store that in user_details["main_goal"].
              - If they mention personal data, parse it with parse_user_details_from_text.
              - Keep calling ask_openai_discovery for a more human-like answer from the assistant.
              - Once we have enough details, switch to 'coaching'.
            """

            # Assistant replies in a discovery style
            discovery_reply = await ask_openai_discovery(user_id, user_text)

            # Check if user mentioned a goal like weight loss
            # Very naive approach: if user says "maigrir" or "perte" or "weight", store main_goal
            if any(word in user_text.lower() for word in ["maigrir", "perdre", "weight", "poids"]):
                user_details["main_goal"] = "perte_de_poids"

            # Parse user’s message for personal details
            parsed = parse_user_details_from_text(user_id, user_text)
            # Merge parsed data
            for key, val in parsed.items():
                if val:
                    user_details[key] = val

            # Example: check if age is found
            have_age = True if user_details.get("age") else False
            have_goal = True if user_details.get("main_goal") else False

            # Save updated details
            create_or_update_user(user_id, {"user_details": user_details})

            # Decide if we remain in discovery or move on
            # Let's do a naive approach: if user has set a main goal AND an age, we move to 'coaching'
            if have_goal and have_age:
                create_or_update_user(user_id, {"conversation_state": "coaching"})
                await event.respond(discovery_reply)
                await event.respond(
                    "Merci pour ces informations. Parlons plus concrètement de votre objectif."
                )
            else:
                # remain in discovery
                await event.respond(discovery_reply)
                await event.respond(
                    "Dites-m'en plus sur vous (votre âge, vos défis, votre objectif) pour que je puisse mieux vous aider."
                )

        # -----------------------------------------
        # STATE: COACHING
        # -----------------------------------------
        else:
            """
            In 'coaching' state, we do normal conversation, but we can also detect 
            if we want to generate a plan once the user is ready.
            """
            # Normal AI response
            reply = ask_openai_normal(user_id, user_text)
            await event.respond(reply)

            # Optionally, if the user says something like "fais moi un plan" or "plan" => generate multi-horizon plan
            if "plan" in user_text.lower():
                # we call generate_multi_horizon_plan using the user_details
                user_goals = user_details.get("main_goal", "un objectif général")
                plan_text = generate_multi_horizon_plan(user_id, user_goals)
                await event.respond(plan_text)

    except Exception as e:
        logger.error(f"Error handling message for user {user_id}: {e}")
        await event.respond("Désolé, il y a un souci de mon côté.")


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

if __name__ == "__main__":
    asyncio.run(main())
