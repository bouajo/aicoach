from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from database import get_user, create_or_update_user
from openai_agent import ask_openai, ask_openai_discovery  # <--- ADDED IMPORT

logger = logging.getLogger(__name__)

app = FastAPI(title="Life Coach API")

class UserMessage(BaseModel):
    user_id: str
    text: str

@app.post("/message")
def handle_message(msg: UserMessage):
    """
    Updated 3-step approach:
      1) 'init' => automatically ask for language
      2) 'waiting_language' => store user's language, then go to 'discovery'
      3) 'discovery' => gather personal info, then go to 'active'
      4) 'active' => pass message to OpenAI
    """
    user_id = msg.user_id.strip()
    text = msg.text.strip()

    user_record = get_user(user_id)

    # If user doesn't exist, create them with conversation_state=init
    if not user_record:
        user_record = create_or_update_user(user_id, {
            "conversation_state": "init",
            "language": "",
            "conversation_summary": {}
        })

    state = user_record.get("conversation_state", "init")

    if state == "init":
        create_or_update_user(user_id, {"conversation_state": "waiting_language"})
        return {"reply": "Hello! Which language would you like to use? (e.g. English, French, Spanish...)"}

    elif state == "waiting_language":
        # Set user language, then go to 'discovery'
        new_language = text.lower()
        create_or_update_user(user_id, {
            "language": new_language,
            "conversation_state": "discovery"
        })
        return {"reply": f"Great! I'll use {new_language}. Tell me more about yourself so I can better understand your situation."}

    elif state == "discovery":
        # We'll do exactly ONE discovery message, then move to 'active'
        discovery_reply = ask_openai_discovery(user_id, text)
        create_or_update_user(user_id, {"conversation_state": "active"})
        return {"reply": discovery_reply}

    else:
        # state='active'
        # Pass the user's text to the normal conversation
        reply_text = ask_openai(user_id, text)
        return {"reply": reply_text}

@app.get("/")
def root():
    return {"message": "Life Coach API is running!"}
