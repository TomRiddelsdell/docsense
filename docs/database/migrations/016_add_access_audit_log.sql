-- Migration 016: Add access audit log table
-- Part of Phase 13: User and Group Authentication
-- See: docs/decisions/021-user-group-authentication-authorization.md

-- ============================================================================
-- ACCESS AUDIT LOG TABLE
-- ============================================================================

-- Audit log for all document access attempts (successful and denied)
CREATE TABLE access_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_kerberos_id VARCHAR(6) NOT NULL,              -- User making the request
    document_id UUID,                                   -- Document being accessed (NULL for list operations)
    action VARCHAR(50) NOT NULL,                        -- Action: view, edit, share, delete, analyze, export
    result VARCHAR(20) NOT NULL,                        -- Result: allowed, denied
    reason TEXT,                                        -- Denial reason or authorization context
    ip_address INET,                                    -- Client IP address
    user_agent TEXT,                                    -- Browser/client user agent
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Foreign key to users (soft reference - user may be deleted)
    CONSTRAINT fk_access_audit_user FOREIGN KEY (user_kerberos_id) 
        REFERENCES users(kerberos_id) ON DELETE SET NULL
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- B-tree index for user audit queries
CREATE INDEX idx_access_audit_user ON access_audit_log(user_kerberos_id);

-- B-tree index for document audit queries
CREATE INDEX idx_access_audit_document ON access_audit_log(document_id);

-- B-tree index for time-based queries (DESC for recent-first)
CREATE INDEX idx_access_audit_occurred_at ON access_audit_log(occurred_at DESC);

-- B-tree index for action filtering
CREATE INDEX idx_access_audit_action ON access_audit_log(action);

-- B-tree index for result filtering (denied events)
CREATE INDEX idx_access_audit_result ON access_audit_log(result);

-- Composite index for common query pattern: user + time range
CREATE INDEX idx_access_audit_user_time ON access_audit_log(user_kerberos_id, occurred_at DESC);

-- Composite index for common query pattern: document + time range
CREATE INDEX idx_access_audit_document_time ON access_audit_log(document_id, occurred_at DESC);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE access_audit_log IS 'Audit trail for all document access attempts (allowed and denied)';
COMMENT ON COLUMN access_audit_log.action IS 'Action type: view, edit, share, delete, analyze, export';
COMMENT ON COLUMN access_audit_log.result IS 'Authorization result: allowed, denied';
COMMENT ON COLUMN access_audit_log.reason IS 'Denial reason (e.g., "not_owner", "insufficient_role") or grant reason';
