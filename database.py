# database.py

import os
import logging
from typing import Optional, Dict
from supabase import create_client, Client
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Please set SUPABASE_URL and SUPABASE_KEY in your .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_user(user_id: str) -> Optional[Dict]:
    """Fetch user record from 'users' table."""
    try:
        response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        data = response.data
        if data and len(data) > 0:
            return data[0]
        return None
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        return None

def create_or_update_user(user_id: str, updates: Dict) -> Dict:
    """Upsert user record. If not exist, create it; else update."""
    try:
        updates["user_id"] = user_id
        response = supabase.table("users").upsert(updates, on_conflict="user_id").execute()
        if response.data and len(response.data) > 0:
            return response.data[0]
        return {}
    except Exception as e:
        logger.error(f"Error creating/updating user {user_id}: {e}")
        return {}

def update_user_summary(user_id: str, new_summary: Dict):
    """Update conversation_summary JSON field in 'users' table."""
    try:
        supabase.table("users").update({"conversation_summary": new_summary}).eq("user_id", user_id).execute()
    except Exception as e:
        logger.error(f"Error updating summary for user {user_id}: {e}")
