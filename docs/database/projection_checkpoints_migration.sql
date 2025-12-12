-- Migration to update projection_checkpoints table for enhanced failure tracking
-- This alters the existing table to add new columns needed for replay capability

-- Add new columns to projection_checkpoints
ALTER TABLE projection_checkpoints 
ADD COLUMN IF NOT EXISTS last_event_type VARCHAR(100),
ADD COLUMN IF NOT EXISTS last_event_sequence BIGINT,
ADD COLUMN IF NOT EXISTS events_processed BIGINT NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS checkpoint_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Update last_event_id to be NOT NULL if it isn't already
ALTER TABLE projection_checkpoints 
ALTER COLUMN last_event_id SET NOT NULL;

-- Rename last_processed_at to align with new naming if it exists
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'projection_checkpoints' 
        AND column_name = 'last_processed_at'
    ) THEN
        -- Copy data to new column and drop old one
        UPDATE projection_checkpoints SET checkpoint_at = last_processed_at WHERE checkpoint_at IS NULL;
        ALTER TABLE projection_checkpoints DROP COLUMN last_processed_at;
    END IF;
END $$;

-- Add index for sequence-based queries
CREATE INDEX IF NOT EXISTS idx_projection_checkpoints_sequence 
    ON projection_checkpoints(last_event_sequence);

-- Add comments
COMMENT ON COLUMN projection_checkpoints.last_event_sequence IS 'Event store sequence number for ordering';
COMMENT ON COLUMN projection_checkpoints.events_processed IS 'Total count of events successfully processed by this projection';
