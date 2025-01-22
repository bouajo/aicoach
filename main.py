# main.py

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from database import get_user, create_or_update_user
from openai_agent import ask_openai

logger = logging.getLogger(__name__)

app = FastAPI(title="Life Coach API")

class UserMessage(BaseModel):
    user_id: str
    text: str
    # For real usage, you might also capture phone number, chat ID, etc.

@app.post("/message")
def handle_message(msg: UserMessage):
    """
    Handle incoming user messages in a simplified 2-step approach:
      1) 'init' => automatically ask for language
      2) 'waiting_language' => store user's language, move to 'active'
      3) 'active' => pass message to OpenAI
    """
    user_id = msg.user_id.strip()
    text = msg.text.strip()

    user_record = get_user(user_id)

    # If user doesn't exist, create them with conversation_state=init
    if not user_record:
        user_record = create_or_update_user(user_id, {
            "conversation_state": "init",
            "language": "",  # not set yet
            "conversation_summary": {}
        })

    state = user_record.get("conversation_state", "init")

    if state == "init":
        # Step 1: Automatic message
        # Update DB state to waiting_language
        create_or_update_user(user_id, {"conversation_state": "waiting_language"})
        return {
            "reply": "Hello! Which language would you like to use? (e.g. English, French, Spanish...)"
        }

    elif state == "waiting_language":
        # Step 2: user is telling us their language
        new_language = text.lower()  # simplistic
        create_or_update_user(user_id, {
            "language": new_language,
            "conversation_state": "active"
        })
        return {
            "reply": f"Great! I'll use {new_language}. What goals or challenges would you like to discuss today?"
        }

    else:
        # 'active' => pass message to OpenAI
        reply_text = ask_openai(user_id, text)
        return {
            "reply": reply_text
        }

@app.get("/")
def root():
    return {"message": "Life Coach API is running!"}
