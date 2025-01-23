import sys
import os
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Application imports
from data.database import db
from data.models import ConversationState
from managers.prompt_manager import PromptManager
from services.ai_service import ai_service

# Configuration
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram configuration
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
PHONE_NUMBER = os.getenv("TELEGRAM_PHONE_NUMBER", "")
SESSION_NAME = "telegram_user_session"

# Initialize managers
prompt_manager = PromptManager()

# Initialize client
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def handle_incoming(event):
    if not event.is_private:
        return
    
    try:
        sender = await event.get_sender()
        user_id = f"tg_{sender.id}"
        user_text = event.raw_text.strip()

        # Get or create user record
        user_record = db.get_user(user_id)
        if not user_record:
            logger.info(f"Creating new user record for {user_id}")
            initial_data = {
                "user_id": user_id,
                "conversation_state": ConversationState.INTRODUCTION.value,
                "language": "français",
                "user_details": {}
            }
            user_record = db.create_or_update_user(user_id, initial_data)
            if not user_record:
                raise Exception("Failed to create user record")

        # Get current state and details
        state = ConversationState(user_record.get("conversation_state", ConversationState.INTRODUCTION.value))
        user_details = user_record.get("user_details", {})
        
        # Get appropriate prompt and AI response
        prompt = prompt_manager.get_prompt(state, user_details)
        ai_response = await ai_service.get_response(prompt, [{"role": "user", "content": user_text}])
        
        # Update conversation history
        if not db.add_conversation_entry(user_id, "user", user_text):
            logger.warning(f"Failed to save user message for {user_id}")
        if not db.add_conversation_entry(user_id, "assistant", ai_response):
            logger.warning(f"Failed to save assistant message for {user_id}")
        
        # Update state
        new_state = state.next_state()
        updated_record = db.create_or_update_user(user_id, {
            "conversation_state": new_state.value,
            "user_details": user_details
        })
        if not updated_record:
            logger.warning(f"Failed to update user state for {user_id}")
        
        await event.respond(ai_response)

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        error_message = (
            "Désolé, j'ai rencontré un problème technique. "
            "Je vais prendre note de cette erreur et la corriger rapidement. "
            "Pourriez-vous réessayer dans quelques instants ?"
        )
        await event.respond(error_message)

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