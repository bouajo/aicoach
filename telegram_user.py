# telegram_user.py

import os
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv

from database import get_user, create_or_update_user
from openai_agent import (
    ask_openai_first_response,
    get_areas_message_in_language,
    generate_plan_for_areas,
    ask_openai_normal,
    PLANS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER", "")

# local session file
SESSION_NAME = "telegram_user_session"

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handle_incoming(event):
    if not event.is_private:
        return  # ignore group messages

    sender = await event.get_sender()
    user_id = f"tg_{sender.id}"
    user_text = event.raw_text.strip()

    # get or create user
    user_record = get_user(user_id)
    if not user_record:
        user_record = create_or_update_user(user_id, {
            "conversation_state": "init",
            "language": "",
            "conversation_summary": {}
        })

    state = user_record.get("conversation_state", "init")

    try:
        if state == "init":
            # user's first message
            reply = ask_openai_first_response(user_id, user_text)
            # set waiting_language
            create_or_update_user(user_id, {"conversation_state": "waiting_language"})
            await event.respond(reply)

        elif state == "waiting_language":
            # user presumably gave or confirmed a language
            create_or_update_user(user_id, {
                "language": user_text,
                "conversation_state": "waiting_areas"
            })
            # get a short bullet-list about areas from GPT
            areas_msg = get_areas_message_in_language(user_text)
            await event.respond(areas_msg)

        elif state == "waiting_areas":
            # user picks area(s)
            # Generate a plan of 5 questions
            user_language = user_record.get("language", "English")
            generate_plan_for_areas(user_id, user_language, user_text)

            # Now we ask the first question
            plan_data = PLANS.get(user_id, {})
            questions = plan_data.get("questions", [])
            if questions:
                first_q = questions[0]
                # set state=asking_questions
                create_or_update_user(user_id, {"conversation_state": "asking_questions"})
                await event.respond(first_q)
            else:
                # no questions? fallback
                create_or_update_user(user_id, {"conversation_state": "active"})
                await event.respond("Ok, let's just chat freely.")
            
        elif state == "asking_questions":
            # the user is answering the current question
            plan_data = PLANS.get(user_id, {})
            questions = plan_data.get("questions", [])
            idx = plan_data.get("index", 0)

            # we store user_text in conversation, but we don't necessarily call GPT yet
            # Then we move to next question if available
            idx += 1
            PLANS[user_id]["index"] = idx

            if idx < len(questions):
                next_q = questions[idx]
                await event.respond(next_q)
            else:
                # we finished all questions
                create_or_update_user(user_id, {"conversation_state": "active"})
                await event.respond("Thanks for answering these questions. Let's continue freely.")
            
        else:
            # state='active'
            reply = ask_openai_normal(user_id, user_text)
            await event.respond(reply)

    except Exception as e:
        logger.error(f"Error handling message for user {user_id}: {e}")
        await event.respond("Sorry, something went wrong on my side.")

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
