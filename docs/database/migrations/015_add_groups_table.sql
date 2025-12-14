-- Migration 015: Add groups reference table
-- Part of Phase 13: User and Group Authentication
-- See: docs/decisions/021-user-group-authentication-authorization.md

-- ============================================================================
-- GROUPS TABLE
-- ============================================================================

-- Groups reference table for organizational groups
-- Groups are synced from authentication system but stored here for display/metadata
CREATE TABLE groups (
    id VARCHAR(255) PRIMARY KEY,        -- Group identifier (e.g., "equity-trading")
    display_name VARCHAR(255) NOT NULL, -- Human-readable name (e.g., "Equity Trading Team")
    description TEXT,                   -- Group description/purpose
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- B-tree index for searching by display name
CREATE INDEX idx_groups_display_name ON groups(display_name);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE groups IS 'Reference table for organizational groups (synced from auth system)';
COMMENT ON COLUMN groups.id IS 'Group identifier used in X-User-Groups header (lowercase, hyphenated)';
COMMENT ON COLUMN groups.display_name IS 'Human-readable group name for UI display';
