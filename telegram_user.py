"""
Telegram bot implementation for the AI coach.
"""

import sys
import os
import asyncio
import logging
import json
import platform
import signal
from datetime import datetime
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv
from pydantic import ValidationError

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Application imports
from data.database import db
from data.models import ConversationState
from data.validators import UserInput
from managers.prompt_manager import PromptManager
from managers.state_manager import StateManager
from services.ai_service import AIService

# Configuration
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('conversation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def is_valid_message(text: str) -> bool:
    """
    Check if message is in French and contains valid content.
    Ignore messages that are clearly not meant for the bot.
    """
    # Ignore empty messages
    if not text or not text.strip():
        return False
        
    # Ignore messages with non-Latin characters (Arabic, Hebrew, etc.)
    if re.search(r'[\u0600-\u06FF\u0590-\u05FF]', text):
        return False
        
    return True

def log_conversation(user_id: str, state: ConversationState, prompt: str, user_message: str, ai_response: str):
    """Log detailed conversation information."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "state": state.value if isinstance(state, ConversationState) else state,
        "prompt": prompt,
        "user_message": user_message,
        "ai_response": ai_response
    }
    logger.info("Conversation details: %s", json.dumps(log_entry, ensure_ascii=False, indent=2))

def get_conversation_state(state_str: str) -> ConversationState:
    """Convert string state to ConversationState enum"""
    try:
        return ConversationState(state_str)
    except ValueError:
        logger.warning(f"Invalid state string: {state_str}, defaulting to INTRODUCTION")
        return ConversationState.INTRODUCTION

async def handle_critical_error(event, error: Exception):
    """Handle critical errors gracefully"""
    logger.error(f"Erreur critique: {str(error)}", exc_info=True)
    # Just log the error, don't send any message
    # This prevents the error message loop

def validate_user_input(text: str, current_state: ConversationState, user_data: dict) -> dict:
    """Validate and extract user input based on current state"""
    try:
        # Create a dict with only the fields we're expecting in current state
        input_data = {}
        
        if current_state == ConversationState.INTRODUCTION:
            if not user_data.get('first_name'):
                input_data['first_name'] = text
            elif not user_data.get('age') and text.isdigit():
                input_data['age'] = int(text)
                
        elif current_state == ConversationState.COLLECTING_DATA:
            # Try to extract height, weight, target weight
            numbers = re.findall(r'\d+(?:\.\d+)?', text)
            if len(numbers) >= 1 and not user_data.get('height'):
                input_data['height'] = int(float(numbers[0]))
            elif len(numbers) >= 1 and not user_data.get('current_weight'):
                input_data['current_weight'] = float(numbers[0])
            elif len(numbers) >= 1 and not user_data.get('target_weight'):
                input_data['target_weight'] = float(numbers[0])
        
        # Validate the extracted data
        if input_data:
            # Merge with existing user data for validation
            full_data = {**user_data, **input_data}
            UserInput(**full_data)  # Validate but don't store result
            return input_data
            
    except ValidationError as e:
        logger.warning(f"Validation error: {str(e)}")
        return {}
        
    return {}

class TelegramCoach:
    def __init__(self):
        self.client = TelegramClient(
            StringSession(os.getenv("TELETHON_SESSION", "")),
            int(os.getenv("TELEGRAM_API_ID")),
            os.getenv("TELEGRAM_API_HASH")
        )
        self.prompt_manager = PromptManager()
        self.ai_service = AIService()
        self.state_manager = StateManager()
        self.shutdown_event = asyncio.Event()
        self._shutdown_requested = False
        self.me = None
        self._error_cooldowns = {}  # Track error message cooldowns per user
        
    async def start(self):
        """Start the client and register handlers"""
        logger.info("Starting Telegram client...")
        
        # Start the client and get our own info
        await self.client.start(phone=os.getenv("TELEGRAM_PHONE_NUMBER"))
        self.me = await self.client.get_me()
        logger.info(f"Connected as {self.me.first_name} ({self.me.phone})")
        
        # Register message handler
        @self.client.on(events.NewMessage(incoming=True))
        async def handle_incoming(event):
            if self.shutdown_event.is_set():
                return  # Don't process new messages during shutdown
                
            # Ignore our own messages
            if event.sender_id == self.me.id:
                return
                
            await self._handle_message(event)
        
        try:
            # Run the client until shutdown is requested
            while not self._shutdown_requested:
                try:
                    await asyncio.sleep(1)  # Check shutdown flag periodically
                except asyncio.CancelledError:
                    break
        finally:
            await self.shutdown()
    
    def request_shutdown(self):
        """Request bot shutdown"""
        self._shutdown_requested = True
    
    async def shutdown(self):
        """Graceful shutdown of the bot"""
        if self.shutdown_event.is_set():
            return  # Prevent multiple shutdown attempts
            
        logger.info("Initiating graceful shutdown...")
        self.shutdown_event.set()
        
        try:
            # Cancel any pending tasks except the current one
            tasks = [t for t in asyncio.all_tasks() 
                    if t is not asyncio.current_task() and not t.done()]
            
            if tasks:
                logger.info(f"Cancelling {len(tasks)} pending tasks...")
                # Cancel all tasks
                for task in tasks:
                    task.cancel()
                
                # Wait for all tasks to complete with timeout
                try:
                    await asyncio.wait(tasks, timeout=5)
                except asyncio.TimeoutError:
                    logger.warning("Some tasks did not complete in time")
            
            # Disconnect client if connected
            if self.client and self.client.is_connected():
                logger.info("Disconnecting Telegram client...")
                await self.client.disconnect()
                
            logger.info("Bot shutdown completed successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}", exc_info=True)
    
    async def _handle_message(self, event):
        """Handle incoming message with proper error handling"""
        try:
            # Get user information
            sender = await event.get_sender()
            user_id = f"tg_{sender.id}"
            user_text = event.raw_text.strip()

            if not is_valid_message(user_text):
                logger.debug(f"Ignoring invalid message from {user_id}: {user_text}")
                return

            logger.info(f"Processing message from {user_id}: {user_text}")

            # Get or create user
            user_data = db.get_user(user_id)
            if not user_data:
                logger.info(f"Creating new user for {user_id}")
                user_data = db.create_user(user_id)
                if not user_data:
                    logger.error("Failed to create user")
                    return

            # Get current state and validate input
            current_state = get_conversation_state(user_data.get('conversation_state', ConversationState.INTRODUCTION.value))
            extracted_data = validate_user_input(user_text, current_state, user_data)
            
            if extracted_data:
                logger.info(f"Extracted validated data: {extracted_data}")
                if not db.update_user(user_id, extracted_data):
                    logger.error("Failed to update user data")
                    return
                user_data = db.get_user(user_id)

            # Get conversation history
            history = db.get_conversation_history(user_id)

            # Generate contextual prompt
            prompt = self.prompt_manager.get_prompt(
                state=current_state,
                context={
                    'user_data': user_data,
                    'history': history[-3:] if history else []
                }
            )

            # Prepare messages for AI
            messages = [
                {"role": "system", "content": prompt},
                *[{"role": msg.role, "content": msg.content} for msg in history[-5:]],
                {"role": "user", "content": user_text}
            ]

            # Get AI response
            ai_response = await self.ai_service.get_response(messages)
            
            # Log conversation details
            log_conversation(
                user_id=user_id,
                state=current_state,
                prompt=prompt,
                user_message=user_text,
                ai_response=ai_response
            )
            
            # Process response and check for state transition
            await self._process_response(event, user_id, ai_response, user_data)

        except Exception as e:
            logger.error(f"Error in message handling: {str(e)}", exc_info=True)
            await handle_critical_error(event, e)
    
    async def _process_response(self, event, user_id: str, response: str, user_data: dict):
        """Process bot response and handle state transitions"""
        try:
            await event.respond(response)

            # Save conversation entries
            db.add_conversation_entry(user_id, "user", event.raw_text.strip())
            db.add_conversation_entry(user_id, "assistant", response)
            
            # Determine next state based on collected data
            current_state = get_conversation_state(user_data.get('conversation_state', ConversationState.INTRODUCTION.value))
            new_state = current_state
            
            if current_state == ConversationState.INTRODUCTION:
                if user_data.get('first_name') and user_data.get('age'):
                    new_state = ConversationState.COLLECTING_DATA
            elif current_state == ConversationState.COLLECTING_DATA:
                if all(user_data.get(field) for field in ['height', 'current_weight', 'target_weight']):
                    new_state = ConversationState.FOLLOW_UP
            
            if new_state != current_state:
                logger.info(f"State transition for {user_id}: {current_state} -> {new_state}")
                db.update_user(user_id, {"conversation_state": new_state.value})

        except Exception as e:
            logger.error(f"Error processing response: {str(e)}", exc_info=True)
            # Don't raise the exception, just log it
            # This prevents the error from propagating and triggering error messages

async def main():
    """Main entry point with platform-specific shutdown handling"""
    coach = TelegramCoach()
    
    if platform.system() != 'Windows':
        # Unix-like systems: Use signal handlers
        def signal_handler():
            logger.info("Received shutdown signal")
            coach.request_shutdown()
        
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_event_loop().add_signal_handler(
                sig,
                signal_handler
            )
    else:
        # Windows: Use asyncio.Event for shutdown
        loop = asyncio.get_event_loop()
        
        def windows_signal_handler(signum, frame):
            logger.info("Received interrupt signal")
            loop.call_soon_threadsafe(coach.request_shutdown)
        
        signal.signal(signal.SIGINT, windows_signal_handler)
    
    try:
        await coach.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
    finally:
        await coach.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)