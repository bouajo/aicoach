"""
Database interface for Supabase.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import httpx
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from all possible locations
env_paths = [
    Path.cwd() / '.env',  # Current directory
    Path.cwd().parent / '.env',  # Parent directory
    Path(__file__).parent.parent / '.env',  # Project root
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        break

# Get database credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError(
        "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are required.\n"
        "Please ensure your .env file exists and contains these variables.\n"
        "Searched in: " + ", ".join(str(p) for p in env_paths)
    )

logger = logging.getLogger(__name__)

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize database connection."""
        if self._initialized:
            return
            
        self.url = SUPABASE_URL
        self.key = SUPABASE_SERVICE_KEY
        
        self.client = httpx.AsyncClient(
            base_url=self.url,
            headers={
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation"
            }
        )
        self._initialized = True
        logger.info(f"Database initialized with service role at {self.url}")

    def _ensure_initialized(self) -> bool:
        """Ensure database is initialized with credentials."""
        if not self._initialized:
            self.__init__()
        return self._initialized

    async def create_tables(self):
        """Create necessary tables if they don't exist."""
        if not hasattr(self, 'client'):
            logger.error("Database client not initialized")
            return
            
        try:
            # Create user_profiles table
            await self.client.post("/rest/v1/rpc/create_user_profiles_if_not_exists", json={
                "sql": """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    first_name TEXT,
                    age INTEGER,
                    height_cm FLOAT,
                    current_weight FLOAT,
                    target_weight FLOAT,
                    language TEXT,
                    language_name TEXT,
                    is_rtl BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_interaction TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    onboarding_completed BOOLEAN DEFAULT FALSE
                );
                """
            })

            # Create conversation_messages table
            await self.client.post("/rest/v1/rpc/create_conversation_messages_if_not_exists", json={
                "sql": """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                    user_id TEXT REFERENCES user_profiles(user_id),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
            })

            # Create conversation_summaries table
            await self.client.post("/rest/v1/rpc/create_conversation_summaries_if_not_exists", json={
                "sql": """
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                    user_id TEXT REFERENCES user_profiles(user_id),
                    summary TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_message_id UUID REFERENCES conversation_messages(id)
                );
                """
            })

            # Create user_context table
            await self.client.post("/rest/v1/rpc/create_user_context_if_not_exists", json={
                "sql": """
                CREATE TABLE IF NOT EXISTS user_context (
                    user_id TEXT PRIMARY KEY REFERENCES user_profiles(user_id),
                    conversation_summary TEXT,
                    last_topics JSONB DEFAULT '[]'::jsonb,
                    last_interaction TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """
            })

            logger.info("Database tables created/verified successfully")
            
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by ID."""
        if not self._ensure_initialized():
            return None
            
        try:
            response = await self.client.get(
                f"/rest/v1/user_profiles",
                params={"select": "*", "user_id": f"eq.{user_id}"}
            )
            response.raise_for_status()
            profiles = response.json()
            return profiles[0] if profiles else None
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None

    async def update_user_profile(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Create or update user profile."""
        if not self._ensure_initialized():
            return False
            
        try:
            # Ensure timestamps are in ISO format
            data["updated_at"] = datetime.utcnow().isoformat()
            if "created_at" not in data:
                data["created_at"] = data["updated_at"]
            
            # Ensure user_id is set
            data["user_id"] = user_id
            
            response = await self.client.post(
                "/rest/v1/user_profiles",
                json=data,
                params={"on_conflict": "user_id"}  # Upsert based on user_id
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error update_user_profile: {e.response.json() if hasattr(e, 'response') else e}")
            return False

    async def add_message(self, user_id: str, role: str, content: str) -> bool:
        """Add a message to the conversation history."""
        if not self._ensure_initialized():
            return False
            
        try:
            response = await self.client.post(
                "/rest/v1/conversation_messages",
                json={
                    "user_id": user_id,
                    "role": role,
                    "content": content,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error add_message: {e.response.json() if hasattr(e, 'response') else e}")
            return False

    async def get_recent_messages(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages for a user."""
        if not self._ensure_initialized():
            return []
            
        try:
            response = await self.client.get(
                f"/rest/v1/conversation_messages",
                params={
                    "select": "*",
                    "user_id": f"eq.{user_id}",
                    "order": "created_at.desc",
                    "limit": str(limit)
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []

    async def get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user context by ID."""
        if not self._ensure_initialized():
            return None
            
        try:
            response = await self.client.get(
                f"/rest/v1/user_context",
                params={"select": "*", "user_id": f"eq.{user_id}"}
            )
            response.raise_for_status()
            contexts = response.json()
            return contexts[0] if contexts else None
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return None

    async def update_user_context(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Update user context."""
        if not self._ensure_initialized():
            return False
            
        try:
            # Ensure timestamps are in ISO format
            data["updated_at"] = datetime.utcnow().isoformat()
            if "created_at" not in data:
                data["created_at"] = data["updated_at"]
            
            # Ensure user_id is set
            data["user_id"] = user_id
            
            response = await self.client.post(
                "/rest/v1/user_context",
                json=data,
                params={"on_conflict": "user_id"}  # Upsert based on user_id
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error update_user_context: {e.response.json() if hasattr(e, 'response') else e}")
            return False

    async def close(self):
        """Close database connection."""
        if hasattr(self, 'client'):
            await self.client.aclose()

# Create a single instance
db = Database()