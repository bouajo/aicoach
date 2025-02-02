"""Script to reset and initialize the database schema."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY are required")

# Initialize Supabase client
client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# SQL to reset and create tables
RESET_SQL = """
-- Drop existing tables in correct order
DROP TABLE IF EXISTS conversation_summaries;
DROP TABLE IF EXISTS conversation_messages;
DROP TABLE IF EXISTS user_profiles;

-- Create user_profiles table
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY,
    first_name TEXT,
    language TEXT DEFAULT 'en',
    language_name TEXT DEFAULT 'English',
    is_rtl BOOLEAN DEFAULT FALSE,
    age INTEGER,
    height_cm INTEGER,
    start_weight FLOAT8,
    current_weight FLOAT8,
    target_weight FLOAT8,
    target_date DATE,
    diet_preferences TEXT[] DEFAULT ARRAY[]::TEXT[],
    diet_restrictions TEXT[] DEFAULT ARRAY[]::TEXT[],
    conversation_state TEXT DEFAULT 'init',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    phone_number TEXT UNIQUE
);

-- Create conversation_messages table with auto-incrementing ID
CREATE TABLE conversation_messages (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(user_id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create conversation_summaries table with auto-incrementing ID
CREATE TABLE conversation_summaries (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(user_id),
    summary TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_messages_user_id ON conversation_messages(user_id);
CREATE INDEX idx_messages_created_at ON conversation_messages(created_at);
CREATE INDEX idx_summaries_user_id ON conversation_summaries(user_id);
"""

def reset_database():
    """Reset and initialize the database schema."""
    try:
        print("Resetting database schema...")
        client.rpc("reset_schema", {"sql_commands": RESET_SQL}).execute()
        print("Database schema reset successfully!")
    except Exception as e:
        print(f"Error resetting database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    reset_database() 