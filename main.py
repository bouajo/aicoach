from fastapi import FastAPI
from data.models import UserData, ConversationState
from data.database import get_user, create_or_update_user
from managers import prompt_manager, state_manager
from services import ai_service

app = FastAPI()
pm = prompt_manager.PromptManager()
sm = state_manager.StateManager()

@app.post("/conversation")
async def handle_conversation(user_id: str, message: str):
    # Get or create user data
    user_record = get_user(user_id)
    if not user_record:
        user_record = create_or_update_user(user_id, {
            "conversation_state": ConversationState.INTRODUCTION.value,
            "user_details": {}
        })
    
    user_data = UserData(**user_record)
    current_state = ConversationState(user_data.conversation_state)
    
    # Get AI response
    prompt = pm.get_prompt(current_state, user_data.dict())
    ai_response = await ai_service.get_response(prompt, [{"role": "user", "content": message}])
    
    # Update state and save data
    new_state = sm.get_next_state(current_state)
    create_or_update_user(user_id, {"conversation_state": new_state.value})
    
    return {"response": ai_response}

@app.get("/user/{user_id}")
async def get_user_data(user_id: str):
    user_record = get_user(user_id)
    if not user_record:
        return {"error": "User not found"}
    return user_record