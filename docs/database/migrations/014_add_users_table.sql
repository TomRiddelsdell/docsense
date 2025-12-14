-- Migration 014: Add users table for authentication
-- Part of Phase 13: User and Group Authentication
-- See: docs/decisions/021-user-group-authentication-authorization.md

-- ============================================================================
-- USERS TABLE
-- ============================================================================

-- Users table for Kerberos-authenticated users
CREATE TABLE users (
    kerberos_id VARCHAR(6) PRIMARY KEY,  -- 6-character Kerberos ID (e.g., "jsmith")
    display_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    groups TEXT[] DEFAULT '{}',          -- Array of group names user belongs to
    roles TEXT[] DEFAULT '{}',           -- Array of role names (viewer, contributor, admin, auditor)
    is_active BOOLEAN DEFAULT TRUE,      -- Account activation status
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- GIN index for fast group membership checks (WHERE 'equity-trading' = ANY(groups))
CREATE INDEX idx_users_groups ON users USING GIN(groups);

-- B-tree index for filtering active users
CREATE INDEX idx_users_is_active ON users(is_active);

-- B-tree index for email lookups
CREATE INDEX idx_users_email ON users(email);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE users IS 'Users authenticated via Kerberos headers (X-User-Id, X-User-Groups)';
COMMENT ON COLUMN users.kerberos_id IS 'Immutable 6-character Kerberos username (primary identity)';
COMMENT ON COLUMN users.groups IS 'Array of group names synced from X-User-Groups header on each login';
COMMENT ON COLUMN users.roles IS 'RBAC roles: viewer, contributor, admin, auditor';
COMMENT ON COLUMN users.is_active IS 'Account activation status (deactivated users cannot access system)';
