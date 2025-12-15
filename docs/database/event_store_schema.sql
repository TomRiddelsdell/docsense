-- Event Store Schema for Trading Algorithm Document Analyzer
-- PostgreSQL database schema following Event Sourcing and CQRS patterns

-- ============================================================================
-- EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- EVENT STORE (Write Side)
-- ============================================================================

-- Core event store table - append-only, immutable
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sequence BIGSERIAL NOT NULL UNIQUE,
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_version INTEGER NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_aggregate_version UNIQUE (aggregate_id, event_version)
);

CREATE INDEX idx_events_aggregate_id ON events(aggregate_id);
CREATE INDEX idx_events_aggregate_type ON events(aggregate_type);
CREATE INDEX idx_events_event_type ON events(event_type);
CREATE INDEX idx_events_created_at ON events(created_at);
CREATE INDEX idx_events_sequence ON events(sequence);

-- Event snapshots for performance optimization
CREATE TABLE snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    state JSONB NOT NULL,
    version INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_snapshot_version UNIQUE (aggregate_id, version)
);

CREATE INDEX idx_snapshots_aggregate_id ON snapshots(aggregate_id);

-- ============================================================================
-- READ MODELS (Query Side)
-- ============================================================================

-- Document Read Model
CREATE TABLE document_views (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    version INTEGER NOT NULL DEFAULT 1,
    original_format VARCHAR(20),
    original_filename VARCHAR(255),
    file_path VARCHAR(500),
    page_count INTEGER,
    content_hash VARCHAR(64),
    policy_repository_id UUID,
    compliance_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_document_views_status ON document_views(status);
CREATE INDEX idx_document_views_policy_repository ON document_views(policy_repository_id);
CREATE INDEX idx_document_views_created_at ON document_views(created_at);

-- Document Content (stored separately for performance)
CREATE TABLE document_contents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES document_views(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    markdown_content TEXT NOT NULL,
    original_content BYTEA,
    sections JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_document_version UNIQUE (document_id, version)
);

CREATE INDEX idx_document_contents_document_id ON document_contents(document_id);

-- Analysis Session Read Model
CREATE TABLE analysis_session_views (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES document_views(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    model_provider VARCHAR(50),
    progress_percent INTEGER DEFAULT 0,
    feedback_count INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analysis_sessions_document_id ON analysis_session_views(document_id);
CREATE INDEX idx_analysis_sessions_status ON analysis_session_views(status);

-- Feedback Read Model
CREATE TABLE feedback_views (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES document_views(id) ON DELETE CASCADE,
    analysis_session_id UUID REFERENCES analysis_session_views(id),
    section_id VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    category VARCHAR(50),
    severity VARCHAR(20) DEFAULT 'info',
    original_text TEXT,
    suggestion TEXT NOT NULL,
    explanation TEXT,
    confidence_score DECIMAL(3,2),
    policy_id UUID,
    policy_reference TEXT,
    rejection_reason TEXT,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feedback_document_id ON feedback_views(document_id);
CREATE INDEX idx_feedback_status ON feedback_views(status);
CREATE INDEX idx_feedback_policy_id ON feedback_views(policy_id);

-- Version History Read Model
CREATE TABLE version_history_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES document_views(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    content_hash VARCHAR(64),
    changes_from_previous INTEGER DEFAULT 0,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_doc_version UNIQUE (document_id, version_number)
);

CREATE INDEX idx_version_history_document_id ON version_history_views(document_id);

-- Policy Repository Read Model
CREATE TABLE policy_repository_views (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    policy_count INTEGER DEFAULT 0,
    document_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_policy_repos_name ON policy_repository_views(name);

-- Policy Read Model
CREATE TABLE policy_views (
    id UUID PRIMARY KEY,
    repository_id UUID NOT NULL REFERENCES policy_repository_views(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    requirement_type VARCHAR(20) NOT NULL,
    validation_rules JSONB DEFAULT '[]',
    ai_prompt_template TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_policies_repository_id ON policy_views(repository_id);
CREATE INDEX idx_policies_requirement_type ON policy_views(requirement_type);

-- Compliance Status Read Model
CREATE TABLE compliance_views (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES document_views(id) ON DELETE CASCADE,
    policy_repository_id UUID REFERENCES policy_repository_views(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    must_total INTEGER DEFAULT 0,
    must_passed INTEGER DEFAULT 0,
    must_failed INTEGER DEFAULT 0,
    should_total INTEGER DEFAULT 0,
    should_passed INTEGER DEFAULT 0,
    should_failed INTEGER DEFAULT 0,
    violations JSONB DEFAULT '[]',
    checked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_doc_compliance UNIQUE (document_id)
);

CREATE INDEX idx_compliance_document_id ON compliance_views(document_id);
CREATE INDEX idx_compliance_status ON compliance_views(status);

-- Audit Log Read Model
CREATE TABLE audit_log_views (
    id UUID PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    aggregate_id UUID,
    aggregate_type VARCHAR(100),
    document_id UUID,
    user_id VARCHAR(255),
    details JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_event_type ON audit_log_views(event_type);
CREATE INDEX idx_audit_log_document_id ON audit_log_views(document_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log_views(timestamp);
CREATE INDEX idx_audit_log_user_id ON audit_log_views(user_id);

-- Semantic IR Read Model (ADR-014)
CREATE TABLE semantic_ir (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES document_views(id) ON DELETE CASCADE,
    ir_type VARCHAR(50) NOT NULL,
    name VARCHAR(500),
    expression TEXT,
    variables JSONB,
    definition TEXT,
    term VARCHAR(500),
    context TEXT,
    table_data JSONB,
    row_count INTEGER,
    column_count INTEGER,
    target VARCHAR(500),
    reference_type VARCHAR(100),
    location TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT semantic_ir_document_fk FOREIGN KEY (document_id)
        REFERENCES document_views(id) ON DELETE CASCADE
);

CREATE INDEX idx_semantic_ir_document_id ON semantic_ir(document_id);
CREATE INDEX idx_semantic_ir_type ON semantic_ir(ir_type);
CREATE INDEX idx_semantic_ir_name ON semantic_ir(name) WHERE name IS NOT NULL;

-- ============================================================================
-- PROJECTION CHECKPOINTS
-- ============================================================================

-- Tracks last processed event for each projection
CREATE TABLE projection_checkpoints (
    projection_name VARCHAR(100) PRIMARY KEY,
    last_event_id UUID,
    last_processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- FILE STORAGE METADATA
-- ============================================================================

CREATE TABLE file_storage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES document_views(id) ON DELETE CASCADE,
    file_type VARCHAR(50) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100),
    file_size BIGINT,
    checksum VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_file_storage_document_id ON file_storage(document_id);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get current aggregate version
CREATE OR REPLACE FUNCTION get_aggregate_version(p_aggregate_id UUID)
RETURNS INTEGER AS $$
DECLARE
    v_version INTEGER;
BEGIN
    SELECT COALESCE(MAX(event_version), 0)
    INTO v_version
    FROM events
    WHERE aggregate_id = p_aggregate_id;
    
    RETURN v_version;
END;
$$ LANGUAGE plpgsql;

-- Function to append event with optimistic concurrency
CREATE OR REPLACE FUNCTION append_event(
    p_aggregate_id UUID,
    p_aggregate_type VARCHAR(100),
    p_event_type VARCHAR(100),
    p_expected_version INTEGER,
    p_payload JSONB,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
    v_current_version INTEGER;
    v_event_id UUID;
BEGIN
    v_current_version := get_aggregate_version(p_aggregate_id);
    
    IF v_current_version != p_expected_version THEN
        RAISE EXCEPTION 'Concurrency conflict: expected version %, got %', 
            p_expected_version, v_current_version;
    END IF;
    
    INSERT INTO events (
        aggregate_id,
        aggregate_type,
        event_type,
        event_version,
        payload,
        metadata
    ) VALUES (
        p_aggregate_id,
        p_aggregate_type,
        p_event_type,
        v_current_version + 1,
        p_payload,
        p_metadata
    ) RETURNING id INTO v_event_id;
    
    RETURN v_event_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get events for aggregate
CREATE OR REPLACE FUNCTION get_aggregate_events(
    p_aggregate_id UUID,
    p_from_version INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    sequence BIGINT,
    event_type VARCHAR(100),
    event_version INTEGER,
    payload JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.sequence,
        e.event_type,
        e.event_version,
        e.payload,
        e.metadata,
        e.created_at
    FROM events e
    WHERE e.aggregate_id = p_aggregate_id
      AND e.event_version > p_from_version
    ORDER BY e.event_version ASC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- TRIGGERS FOR UPDATED_AT
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_document_views_updated_at
    BEFORE UPDATE ON document_views
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_policy_repository_views_updated_at
    BEFORE UPDATE ON policy_repository_views
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_policy_views_updated_at
    BEFORE UPDATE ON policy_views
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_compliance_views_updated_at
    BEFORE UPDATE ON compliance_views
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE events IS 'Append-only event store - source of truth for all state changes';
COMMENT ON TABLE snapshots IS 'Aggregate state snapshots for performance optimization';
COMMENT ON TABLE document_views IS 'Read model for document list and details';
COMMENT ON TABLE document_contents IS 'Versioned document content storage';
COMMENT ON TABLE analysis_session_views IS 'Read model for analysis session status';
COMMENT ON TABLE feedback_views IS 'Read model for AI-generated feedback items';
COMMENT ON TABLE version_history_views IS 'Read model for document version timeline';
COMMENT ON TABLE policy_repository_views IS 'Read model for policy repositories';
COMMENT ON TABLE policy_views IS 'Read model for individual policies';
COMMENT ON TABLE compliance_views IS 'Read model for document compliance status';
COMMENT ON TABLE audit_log_views IS 'Read model for audit trail entries';
COMMENT ON TABLE projection_checkpoints IS 'Tracks projection processing state for replay';
COMMENT ON TABLE file_storage IS 'Metadata for stored files (original uploads, exports)';
