"""
API routes for the application.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.chat_service import chat_service
from services.ai_service import AIProvider

router = APIRouter()

class MessageRequest(BaseModel):
    user_id: str
    message: str
    provider: Optional[AIProvider] = None

class MessageResponse(BaseModel):
    response: str
    user_data: dict

@router.post("/conversation", response_model=MessageResponse)
async def handle_conversation(request: MessageRequest):
    """Process a conversation message."""
    try:
        response, user_data = await chat_service.process_message(
            user_id=request.user_id,
            message=request.message,
            provider=request.provider
        )
        return MessageResponse(response=response, user_data=user_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 