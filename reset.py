"""
Script to reset all data in Supabase database.
This script will clear all records from the tables.
NOTE: Tables must be created first using Supabase's dashboard SQL editor.
"""

import asyncio
import logging
from typing import List, Dict
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Supabase client with service role key
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY is required in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logger.info("Initialized Supabase client with service role key")

# SQL for creating tables (to be executed in Supabase SQL editor)
SETUP_SQL = """
-- Create tables for the AI Coach application

-- User Profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id UUID PRIMARY KEY,
    first_name TEXT,
    language TEXT,
    language_name TEXT,
    is_rtl BOOLEAN DEFAULT FALSE,
    age INTEGER,
    height_cm INTEGER,
    start_weight FLOAT,
    current_weight FLOAT,
    target_weight FLOAT,
    target_date DATE,
    diet_preferences TEXT[],
    diet_restrictions TEXT[],
    conversation_state TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Conversation Messages table
CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(user_id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Conversation Summaries table
CREATE TABLE IF NOT EXISTS conversation_summaries (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(user_id),
    summary TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_conversation_messages_user_id ON conversation_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_summaries_user_id ON conversation_summaries(user_id);
"""

def print_setup_instructions():
    """Print instructions for setting up tables."""
    print("\n⚠️  IMPORTANT: Before running this script for the first time:")
    print("1. Go to your Supabase dashboard")
    print("2. Open the SQL editor")
    print("3. Copy and paste the following SQL to create the tables:")
    print("\n" + "="*50 + " SQL SETUP " + "="*50)
    print(SETUP_SQL)
    print("="*110 + "\n")

async def check_table_exists(table_name: str) -> bool:
    """
    Check if a table exists in Supabase.
    
    Args:
        table_name: Name of the table to check
        
    Returns:
        bool: True if table exists, False otherwise
    """
    try:
        data = supabase.table(table_name).select("*").limit(1).execute()
        return True
    except Exception as e:
        if "'42P01'" in str(e):  # Table doesn't exist error
            return False
        raise

async def ensure_tables_exist() -> None:
    """Check if all required tables exist."""
    tables = ["user_profiles", "conversation_messages", "conversation_summaries"]
    missing_tables = []
    
    for table in tables:
        if not await check_table_exists(table):
            missing_tables.append(table)
    
    if missing_tables:
        print("\n❌ Error: The following tables are missing:")
        for table in missing_tables:
            print(f"  - {table}")
        print_setup_instructions()
        raise Exception("Missing required tables")

async def reset_table(table_name: str) -> None:
    """
    Reset a specific table in Supabase.

    Args:
        table_name: Name of the table to reset
    """
    try:
        # Different tables have different primary key columns
        pk_column = "user_id" if table_name == "user_profiles" else "id"
        
        # Get all records first
        data = supabase.table(table_name).select(pk_column).execute()
        if data.data:
            # Delete records in batches to avoid timeouts
            batch_size = 100
            for i in range(0, len(data.data), batch_size):
                batch = data.data[i:i + batch_size]
                ids = [record[pk_column] for record in batch]
                supabase.table(table_name).delete().in_(pk_column, ids).execute()
                logger.info(f"Deleted batch of {len(batch)} records from {table_name}")
        
        logger.info(f"Successfully cleared table: {table_name}")
        
    except Exception as e:
        logger.error(f"Error clearing table {table_name}: {e}")
        raise

async def reset_all_tables() -> None:
    """Reset all tables in the database."""
    # List of tables to reset in correct order (respect foreign keys)
    tables = [
        "conversation_messages",
        "conversation_summaries",
        "user_profiles"
    ]
    
    try:
        logger.info("Starting database reset...")
        
        # First ensure all tables exist
        await ensure_tables_exist()
        
        # Reset each table in order (child tables first)
        for table in tables:
            await reset_table(table)
            
        logger.info("Database reset completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during database reset: {e}")
        raise

def main():
    """Main function to run the reset script."""
    try:
        # Print warning
        print("\n⚠️  WARNING: This will delete all data from the database!")
        print("Are you sure you want to continue? (y/N)")
        
        # Get user confirmation
        response = input().lower()
        if response != 'y':
            print("Reset cancelled.")
            return
        
        # Run the reset
        asyncio.run(reset_all_tables())
        print("\n✅ Database reset completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main() 