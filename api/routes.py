"""
API routes for business logic (e.g., /conversation, /status, etc.)
"""

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    return {"message": "Welcome to the AI Coach API (WhatsApp Only)!"} 