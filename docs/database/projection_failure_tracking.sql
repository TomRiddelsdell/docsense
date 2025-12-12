-- Projection Failure Tracking Tables
-- 
-- These tables support Event Sourcing projection resilience by:
-- 1. Tracking failed projection attempts for retry and monitoring
-- 2. Maintaining checkpoints for each projection to enable replay
-- 3. Supporting compensation logic and manual recovery

-- Table: projection_failures
-- Tracks all projection failure attempts with retry information
CREATE TABLE IF NOT EXISTS projection_failures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    projection_name VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    error_traceback TEXT,
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 5,
    failed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_retry_at TIMESTAMP,
    next_retry_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_method VARCHAR(50), -- 'auto_retry', 'manual_replay', 'compensated'
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_projection_failures_projection_name 
    ON projection_failures(projection_name);
    
CREATE INDEX IF NOT EXISTS idx_projection_failures_event_id 
    ON projection_failures(event_id);
    
CREATE INDEX IF NOT EXISTS idx_projection_failures_unresolved 
    ON projection_failures(projection_name, resolved_at) 
    WHERE resolved_at IS NULL;
    
CREATE INDEX IF NOT EXISTS idx_projection_failures_retry_due 
    ON projection_failures(next_retry_at) 
    WHERE resolved_at IS NULL AND next_retry_at IS NOT NULL;

-- Table: projection_checkpoints
-- Tracks the last successfully processed event for each projection
-- Enables replay from last known good state
CREATE TABLE IF NOT EXISTS projection_checkpoints (
    projection_name VARCHAR(100) PRIMARY KEY,
    last_event_id UUID NOT NULL,
    last_event_type VARCHAR(100) NOT NULL,
    last_event_sequence BIGINT NOT NULL,
    checkpoint_at TIMESTAMP NOT NULL DEFAULT NOW(),
    events_processed BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Index for querying checkpoint positions
CREATE INDEX IF NOT EXISTS idx_projection_checkpoints_sequence 
    ON projection_checkpoints(last_event_sequence);

-- Table: projection_health_metrics
-- Aggregated metrics for projection health monitoring
CREATE TABLE IF NOT EXISTS projection_health_metrics (
    projection_name VARCHAR(100) PRIMARY KEY,
    total_events_processed BIGINT NOT NULL DEFAULT 0,
    total_failures BIGINT NOT NULL DEFAULT 0,
    active_failures BIGINT NOT NULL DEFAULT 0,
    last_failure_at TIMESTAMP,
    last_success_at TIMESTAMP,
    avg_processing_time_ms DECIMAL(10, 2),
    lag_seconds BIGINT,
    health_status VARCHAR(20) NOT NULL DEFAULT 'healthy', -- 'healthy', 'degraded', 'critical', 'offline'
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Comments for documentation
COMMENT ON TABLE projection_failures IS 'Tracks projection failure attempts with retry information for Event Sourcing resilience';
COMMENT ON TABLE projection_checkpoints IS 'Maintains last successfully processed event per projection for replay capability';
COMMENT ON TABLE projection_health_metrics IS 'Aggregated health metrics for projection monitoring and alerting';

COMMENT ON COLUMN projection_failures.retry_count IS 'Number of retry attempts made for this failure';
COMMENT ON COLUMN projection_failures.next_retry_at IS 'Scheduled time for next retry attempt (exponential backoff)';
COMMENT ON COLUMN projection_failures.resolution_method IS 'How the failure was resolved: auto_retry, manual_replay, or compensated';

COMMENT ON COLUMN projection_checkpoints.last_event_sequence IS 'Event store sequence number for ordering';
COMMENT ON COLUMN projection_checkpoints.events_processed IS 'Total count of events successfully processed by this projection';

COMMENT ON COLUMN projection_health_metrics.lag_seconds IS 'Time difference between latest event and last processed event';
COMMENT ON COLUMN projection_health_metrics.health_status IS 'Overall health: healthy, degraded (some failures), critical (many failures), offline (not processing)';
