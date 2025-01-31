-- Add start_weight column to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS start_weight NUMERIC;

-- Update existing records to copy current_weight to start_weight if needed
UPDATE users 
SET start_weight = current_weight 
WHERE start_weight IS NULL AND current_weight IS NOT NULL;

-- Add comment to explain the column
COMMENT ON COLUMN users.start_weight IS 'Initial weight when user starts the program';
COMMENT ON COLUMN users.current_weight IS 'Current weight, updated during progress tracking'; 