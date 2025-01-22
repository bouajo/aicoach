README
Project Overview
This repository implements a simple “Life Coach” application that interacts with users via:

HTTP API (via FastAPI in main.py), and
Telegram (via the Telethon library in telegram.py and telegram_user.py).
The AI portion is powered by OpenAI’s GPT models (openai_agent.py). User data (like conversation state, language preferences, etc.) is stored in a Supabase database (database.py).

Main Features
User Management: The system can identify and store user information, track their current conversation state, and remember conversation summaries.
Conversation Flow: Basic multi-step flow (initial greeting, ask for language, gather info, then proceed to “active” free-form conversation).
OpenAI Integration: The system calls GPT-3.5-turbo to generate responses, with different prompts for different stages of the conversation.
Telegram Bot: A simple bot that responds to incoming messages and delegates the conversation logic to our AI.
Telegram “User” Simulation: A second script that can act as a “user” client for testing or demonstration (though you can also just chat with the bot as a normal user).
File-by-File Explanation
1. requirements.txt
Lists all Python dependencies:

fastapi + uvicorn: For the HTTP API.
python-dotenv: For loading environment variables from .env.
openai: Required to call the OpenAI GPT API.
supabase + httpx: For interacting with a Supabase database.
telethon: For creating a Telegram client/bot.
2. .env (not included in the repo, but required)
Should define the following environment variables (examples):

makefile
Copier
SUPABASE_URL=<your_supabase_project_url>
SUPABASE_KEY=<your_supabase_anon_or_service_key>

OPENAI_API_KEY=<your_openai_api_key>

TELEGRAM_API_ID=<telegram_api_id>
TELEGRAM_API_HASH=<telegram_api_hash>
TELEGRAM_BOT_TOKEN=<telegram_bot_token>
TELEGRAM_PHONE_NUMBER=<phone_number_for_telegram_user>
3. database.py
Purpose: Interacts with the Supabase database to store and retrieve user data.
Functions:
get_user(user_id: str) -> Optional[Dict]: Retrieves a user’s record (if any) from the users table.
create_or_update_user(user_id: str, updates: Dict) -> Dict: Inserts a new record or updates an existing record with the same user_id.
update_user_summary(user_id: str, new_summary: Dict): Specifically updates the conversation_summary JSON field for a user.
4. main.py
Purpose: FastAPI application that exposes HTTP endpoints for the Life Coach logic.
Endpoints:
POST /message: Accepts a JSON body with user_id and text. Based on the user’s conversation state, it handles:
init → Asks the user which language they want.
waiting_language → Stores the chosen language, transitions to “active”.
active → Passes the user message to OpenAI and returns the AI’s reply.
GET /: Basic health-check endpoint.
5. openai_agent.py
Purpose: Central place for calling GPT and managing in-memory conversation data (if any).

Key Dictionaries:

CONVERSATIONS: A Python dict { user_id: [list of message dicts] } that holds recent messages for each user.
PLANS: Another dict to store a plan/agenda of questions. Example:
py
Copier
{
  user_id: {
    "questions": ["Q1", "Q2", ...],
    "index": 0
  }
}
System Prompts:

INITIAL_SYSTEM_PROMPT: Used during the very first user message (detect language, greet in that language, etc.).
AREAS_SYSTEM_PROMPT: Used to produce a bullet list of possible focus areas in the user’s chosen language.
PLAN_SYSTEM_PROMPT: Used to create a 5-question plan based on user-selected areas.
MAIN_SYSTEM_PROMPT: Used in ongoing, free-form conversation to keep a friendly, human-like tone.
Functions:

_add_msg: Helper to add a message (user or assistant) to CONVERSATIONS.
_recent_msgs: Returns the last N messages for a user.
_summary_from_convo: Creates a naive summary from the last 3 user messages.
_call_gpt: Generic wrapper to call GPT (with system prompt + user messages).
ask_openai_first_response: Entry point for the very first user message.
get_areas_message_in_language: Generate bullet-list of areas in the user’s language.
generate_plan_for_areas: Creates 5 short questions to help the user (and stores them in PLANS).
ask_openai_normal: Normal conversation once in the “active” or free-form state.
6. telegram.py
Purpose: A Telegram Bot implementation using Telethon.
Flow:
Initializes a TelegramClient with bot credentials.
Listens for new messages (events.NewMessage).
Fetches/creates user record from the DB.
Based on conversation_state, either asks for the language or delegates to ask_openai from openai_agent.py.
Responds to the user via Telegram.
7. telegram_user.py
Purpose: A Telegram client script that can act like a user (or a test user). This is useful if you want to simulate conversation from another phone number/account.
Flow:
Connects to Telegram with your phone number (must be different from the bot’s).
Listens for incoming messages in private chat.
Uses the same logic as telegram.py but with a more detailed, multi-step approach (init → waiting_language → waiting_areas → asking_questions → active).
Calls different functions from openai_agent.py depending on the user’s state.
8. run.py
Purpose: Simple script to run the FastAPI app with uvicorn.
Command:
arduino
Copier
python run.py
This will start the Life Coach API on localhost:8000.
Setting Up & Running
Clone the Repository:

bash
Copier
git clone <repo_url>
cd bouajo-aicoach.git
Create a Python Virtual Environment (recommended):

bash
Copier
python -m venv venv
source venv/bin/activate  # or "venv\Scripts\activate" on Windows
Install Dependencies:

bash
Copier
pip install -r requirements.txt
Configure .env:

Create a .env file (in the same directory) with keys for Supabase, OpenAI, and Telegram. Example:
ini
Copier
SUPABASE_URL=https://your-supabase-url.supabase.co
SUPABASE_KEY=your-supabase-anon-key

OPENAI_API_KEY=sk-...

TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=abc123...
TELEGRAM_BOT_TOKEN=54321:AAAA...
TELEGRAM_PHONE_NUMBER=+19876543210
Run the API:

bash
Copier
python run.py
Visit http://localhost:8000/ to see "Life Coach API is running!".
Run the Telegram Bot:

bash
Copier
python telegram.py
This logs in as the bot.
You can then open Telegram, find your bot, and start chatting.
(Optional) Run the “User” Client:

bash
Copier
python telegram_user.py
This logs in as a regular user (with the phone number you provided in .env).
You can then programmatically send messages to test your bot in private.
How the Conversation Works (High-Level)
Database: Each user has a record in the users table with fields like:

user_id
language
conversation_state
conversation_summary (storing short summary of the conversation)
etc.
Conversation State:

init: The first time we see a user, we greet them and ask for their language.
waiting_language: We store their chosen language in DB, move to the next step.
waiting_areas (only in telegram_user.py flow): We ask them which areas they want to focus on.
asking_questions (only in telegram_user.py flow): We have a list of 5 questions. We step through each.
active: Once the initial setup is done, we ask GPT to respond to user messages in a more free-form manner.
GPT Usage:

A few specialized system prompts for different phases (detect language, produce bullet-list, generate plan, normal chat).
We store a short conversation history for context.