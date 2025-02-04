-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop existing table if it exists
DROP TABLE IF EXISTS user_profiles;

-- Create user_profiles table with proper constraints and data types
CREATE TABLE user_profiles (
    -- Primary key and identification
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number TEXT NOT NULL UNIQUE,
    
    -- Basic profile fields
    language TEXT DEFAULT 'und',
    step TEXT DEFAULT 'new',
    name TEXT,
    age NUMERIC CHECK (age > 0 AND age < 120),
    
    -- Physical measurements
    start_weight NUMERIC CHECK (start_weight > 0 AND start_weight < 500),
    current_weight NUMERIC CHECK (current_weight > 0 AND current_weight < 500),
    target_weight NUMERIC CHECK (target_weight > 0 AND target_weight < 500),
    height NUMERIC CHECK (height > 0 AND height < 300),
    
    -- Additional profile data
    activity_level TEXT,
    dietary_restrictions TEXT[],
    health_conditions TEXT[],
    
    -- Diet plan and goals
    plan JSONB,
    goals JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    plan_created_at TIMESTAMPTZ,
    
    -- Add check constraints for enum-like fields
    CONSTRAINT valid_language CHECK (language ~ '^[a-z]{2}$' OR language = 'und'),
    CONSTRAINT valid_step CHECK (step IN ('new', 'language_detected', 'profile_complete', 'chat'))
);

-- Create index on phone_number for faster lookups
CREATE INDEX idx_user_profiles_phone ON user_profiles(phone_number);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE user_profiles IS 'Stores user profiles for the AI diet coach application';
COMMENT ON COLUMN user_profiles.user_id IS 'Unique identifier for the user';
COMMENT ON COLUMN user_profiles.phone_number IS 'User''s phone number (WhatsApp)';
COMMENT ON COLUMN user_profiles.language IS 'User''s preferred language (ISO 639-1 code)';
COMMENT ON COLUMN user_profiles.step IS 'Current step in the user journey';
COMMENT ON COLUMN user_profiles.name IS 'User''s preferred name';
COMMENT ON COLUMN user_profiles.age IS 'User''s age in years';
COMMENT ON COLUMN user_profiles.start_weight IS 'Initial weight in kg';
COMMENT ON COLUMN user_profiles.current_weight IS 'Current weight in kg';
COMMENT ON COLUMN user_profiles.target_weight IS 'Target weight in kg';
COMMENT ON COLUMN user_profiles.height IS 'Height in cm';
COMMENT ON COLUMN user_profiles.activity_level IS 'User''s activity level';
COMMENT ON COLUMN user_profiles.dietary_restrictions IS 'Array of dietary restrictions';
COMMENT ON COLUMN user_profiles.health_conditions IS 'Array of health conditions';
COMMENT ON COLUMN user_profiles.plan IS 'JSON containing the user''s diet plan';
COMMENT ON COLUMN user_profiles.goals IS 'JSON containing the user''s goals'; 