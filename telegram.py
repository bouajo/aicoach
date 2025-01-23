import os
import logging
import asyncio
from telethon import TelegramClient, events
from deepseek_agent import ask_coach_response  # Changed import
from data.database import get_user, create_or_update_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = os.getenv("TELEGRAM_API_ID", "")
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

client = TelegramClient("life_coach_bot", API_ID, API_HASH)

@client.on(events.NewMessage)
async def handle_telegram_message(event):
    sender_id = event.sender_id
    text = event.raw_text.strip()
    user_id = str(sender_id)

    user_record = get_user(user_id)
    if not user_record:
        user_record = create_or_update_user(user_id, {
            "conversation_state": "init",
            "language": "",
            "conversation_summary": {}
        })

    state = user_record.get("conversation_state", "init")

    if state == "init":
        create_or_update_user(user_id, {"conversation_state": "waiting_language"})
        await event.respond("Hello! Which language would you like to use?")
    elif state == "waiting_language":
        new_language = text.lower()
        create_or_update_user(user_id, {"language": new_language, "conversation_state": "active"})
        await event.respond(f"Great! I'll use {new_language}. What goals or challenges would you like to discuss today?")
    else:
        reply = await ask_coach_response(user_id, text)
        await event.respond(reply)

async def start_telegram_bot():
    await client.start(bot_token=BOT_TOKEN)
    logger.info("Telegram Bot started. Waiting for messages...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(start_telegram_bot())