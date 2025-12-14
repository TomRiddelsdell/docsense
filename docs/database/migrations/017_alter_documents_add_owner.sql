-- Migration 017: Add ownership columns to document_views
-- Part of Phase 13: User and Group Authentication
-- See: docs/decisions/021-user-group-authentication-authorization.md

-- ============================================================================
-- ALTER DOCUMENT_VIEWS TABLE
-- ============================================================================

-- Add ownership column (nullable initially for backfill)
ALTER TABLE document_views 
ADD COLUMN owner_kerberos_id VARCHAR(6);

-- Add visibility column with default 'private'
ALTER TABLE document_views 
ADD COLUMN visibility VARCHAR(20) DEFAULT 'private' NOT NULL;

-- Add shared_with_groups array column
ALTER TABLE document_views 
ADD COLUMN shared_with_groups TEXT[] DEFAULT '{}' NOT NULL;

-- ============================================================================
-- BACKFILL EXISTING DATA
-- ============================================================================

-- Set 'system' as owner for all existing documents
-- This preserves existing documents while enforcing ownership for new ones
UPDATE document_views 
SET owner_kerberos_id = 'system' 
WHERE owner_kerberos_id IS NULL;

-- ============================================================================
-- ADD NOT NULL CONSTRAINT (after backfill)
-- ============================================================================

-- Now that all documents have an owner, make it NOT NULL
ALTER TABLE document_views 
ALTER COLUMN owner_kerberos_id SET NOT NULL;

-- ============================================================================
-- ADD FOREIGN KEY CONSTRAINT
-- ============================================================================

-- Foreign key to users (soft reference - allows 'system' user)
-- We don't add the FK constraint to allow 'system' as a special owner
-- without requiring a 'system' user in the users table

-- ============================================================================
-- INDEXES
-- ============================================================================

-- B-tree index for owner queries (my documents)
CREATE INDEX idx_document_views_owner ON document_views(owner_kerberos_id);

-- B-tree index for visibility filtering
CREATE INDEX idx_document_views_visibility ON document_views(visibility);

-- GIN index for fast group membership checks (shared_with_groups)
CREATE INDEX idx_document_views_shared_groups ON document_views USING GIN(shared_with_groups);

-- Composite index for common query: owner + visibility
CREATE INDEX idx_document_views_owner_visibility ON document_views(owner_kerberos_id, visibility);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON COLUMN document_views.owner_kerberos_id IS 'Document owner (immutable, set on upload)';
COMMENT ON COLUMN document_views.visibility IS 'Visibility level: private, group, organization, public';
COMMENT ON COLUMN document_views.shared_with_groups IS 'Array of group IDs document is shared with';

-- ============================================================================
-- VALIDATION
-- ============================================================================

-- Add CHECK constraint for visibility values
ALTER TABLE document_views 
ADD CONSTRAINT check_visibility 
CHECK (visibility IN ('private', 'group', 'organization', 'public'));
