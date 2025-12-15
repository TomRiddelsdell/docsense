# Database Migration Runbook

## Overview

This runbook provides step-by-step procedures for managing database schema changes in the Trading Algorithm Document Analyzer application using event sourcing and CQRS patterns.

**Important:** Event sourcing requires special care during migrations. Events are immutable and must NEVER be deleted or modified. This runbook follows event sourcing best practices.

---

## Table of Contents

1. [Migration Strategy](#migration-strategy)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [Migration Procedures](#migration-procedures)
4. [Post-Migration Verification](#post-migration-verification)
5. [Rollback Procedures](#rollback-procedures)
6. [Common Migration Scenarios](#common-migration-scenarios)
7. [Troubleshooting](#troubleshooting)

---

## Migration Strategy

### Event Sourcing Principles

1. **Events are immutable** - Never modify or delete existing events
2. **Schema evolution** - Use event upcasting for event schema changes
3. **Read model flexibility** - Read models can be rebuilt from events
4. **Zero-downtime migrations** - Most migrations can be done without downtime

### Migration Types

#### Type 1: Event Store Schema Changes
**Examples:** Adding columns, indexes, constraints to `events` table

**Risk:** Medium - Affects core event persistence

**Downtime:** May require brief downtime for structural changes

#### Type 2: Read Model Changes
**Examples:** Adding tables, columns to `document_views`, `feedback_views`

**Risk:** Low - Can rebuild from events

**Downtime:** Usually zero - rebuild projections asynchronously

#### Type 3: Event Schema Changes
**Examples:** Adding fields to event payloads

**Risk:** Low - Use event upcasting

**Downtime:** Zero - backward compatible with upcasters

---

## Pre-Migration Checklist

Before running any database migration:

- [ ] **Backup database** (see [Backup Procedure](#backup-procedure))
- [ ] **Test in staging** - Apply migration to staging environment first
- [ ] **Review migration script** - Verify SQL is correct and idempotent
- [ ] **Check event count** - Note current event count for verification
- [ ] **Verify disk space** - Ensure sufficient space for migration
- [ ] **Schedule maintenance window** (if downtime required)
- [ ] **Notify stakeholders** - Inform team of planned migration
- [ ] **Prepare rollback plan** - Document rollback steps
- [ ] **Review recent events** - Check for any anomalies in event stream

### Backup Procedure

```bash
# Set variables
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/docsense"
DATABASE_URL="postgresql://user:password@host:5432/docsense_prod"

# Create backup directory
mkdir -p $BACKUP_DIR

# Full database backup
pg_dump $DATABASE_URL > $BACKUP_DIR/docsense_$TIMESTAMP.sql

# Compressed backup (recommended)
pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/docsense_$TIMESTAMP.sql.gz

# Events-only backup (fastest to restore critical data)
pg_dump $DATABASE_URL -t events -t snapshots | gzip > $BACKUP_DIR/events_$TIMESTAMP.sql.gz

# Verify backup
gunzip -c $BACKUP_DIR/docsense_$TIMESTAMP.sql.gz | head -n 20

# Store backup securely
aws s3 cp $BACKUP_DIR/docsense_$TIMESTAMP.sql.gz s3://backups/docsense/
```

**Retention Policy:**
- Daily backups: Keep 7 days
- Weekly backups: Keep 4 weeks
- Monthly backups: Keep 12 months

---

## Migration Procedures

### Procedure 1: Adding Sequence Column to Events Table

**File:** `/workspaces/scripts/migrate_add_sequence_column.py`

**Purpose:** Add BIGSERIAL sequence column for global event ordering

**Risk Level:** Medium

**Estimated Duration:** 5-15 minutes (depending on event count)

#### Steps

1. **Review Migration Script**

```bash
# View the migration script
cat /workspaces/scripts/migrate_add_sequence_column.py

# Check current event count
psql $DATABASE_URL -c "SELECT COUNT(*) as event_count FROM events;"
```

2. **Run Migration in Staging**

```bash
# Apply to staging first
STAGING_DATABASE_URL="postgresql://..." \
  python scripts/migrate_add_sequence_column.py

# Verify in staging
psql $STAGING_DATABASE_URL -c "\d events"
psql $STAGING_DATABASE_URL -c "SELECT MIN(sequence), MAX(sequence), COUNT(*) FROM events;"
```

3. **Schedule Production Migration**

```bash
# Recommended: Brief maintenance window (5-10 minutes)
# Reason: Adding column with BIGSERIAL requires table lock

# Set maintenance mode (optional - if using load balancer)
# curl -X POST https://loadbalancer/maintenance/enable
```

4. **Backup Production Database**

```bash
# See backup procedure above
pg_dump $DATABASE_URL | gzip > /backups/before_sequence_$TIMESTAMP.sql.gz
```

5. **Run Migration in Production**

```bash
cd /workspaces

# Run migration
DATABASE_URL=$DATABASE_URL python scripts/migrate_add_sequence_column.py

# Expected output:
# ✓ Added sequence column to events table
# ✓ Created index on sequence
# ✓ Backfilled sequence for 44 existing events
# ✓ Sequence range: 1 to 44
# ✅ Migration completed successfully!
```

6. **Verify Migration**

```bash
# Check schema
psql $DATABASE_URL -c "\d events"

# Verify sequence column exists and has UNIQUE constraint
psql $DATABASE_URL -c "
  SELECT
    column_name,
    data_type,
    is_nullable
  FROM information_schema.columns
  WHERE table_name = 'events' AND column_name = 'sequence';
"

# Verify index exists
psql $DATABASE_URL -c "\di idx_events_sequence"

# Verify sequence values
psql $DATABASE_URL -c "
  SELECT
    COUNT(*) as total_events,
    MIN(sequence) as min_seq,
    MAX(sequence) as max_seq,
    COUNT(DISTINCT sequence) as unique_sequences
  FROM events;
"

# Verify no gaps (optional)
psql $DATABASE_URL -c "
  WITH expected_range AS (
    SELECT generate_series(
      (SELECT MIN(sequence) FROM events),
      (SELECT MAX(sequence) FROM events)
    ) AS expected_seq
  )
  SELECT
    COUNT(*) as missing_sequences
  FROM expected_range
  WHERE expected_seq NOT IN (SELECT sequence FROM events);
"
```

7. **Restart Application**

```bash
# Restart to use new sequence column
sudo systemctl restart docsense

# Watch logs
sudo journalctl -u docsense -f
```

8. **Clear Maintenance Mode**

```bash
# Re-enable traffic
# curl -X POST https://loadbalancer/maintenance/disable
```

---

### Procedure 2: Creating semantic_ir Table

**File:** `/workspaces/scripts/migrate_create_semantic_ir_table.py`

**Purpose:** Create table for storing semantic intermediate representation

**Risk Level:** Low (new table, no data modification)

**Estimated Duration:** 1-2 minutes

#### Steps

1. **Review Migration Script**

```bash
cat /workspaces/scripts/migrate_create_semantic_ir_table.py

# Verify table doesn't already exist
psql $DATABASE_URL -c "\dt semantic_ir"
```

2. **Run Migration**

```bash
cd /workspaces

# Run migration
DATABASE_URL=$DATABASE_URL python scripts/migrate_create_semantic_ir_table.py

# Expected output:
# ✓ Created semantic_ir table
# ✓ Created index on document_id
# ✓ Created index on ir_type
# ✓ Created index on name
# ✓ Total semantic_ir records: 0
# ✅ Migration completed successfully!
```

3. **Verify Migration**

```bash
# Check table exists
psql $DATABASE_URL -c "\d semantic_ir"

# Verify indexes
psql $DATABASE_URL -c "\di idx_semantic_ir_*"

# Verify foreign key constraint
psql $DATABASE_URL -c "
  SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
  FROM information_schema.table_constraints AS tc
  JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
  JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
  WHERE tc.table_name = 'semantic_ir'
    AND tc.constraint_type = 'FOREIGN KEY';
"
```

**No application restart required** - Application will automatically detect new table.

---

### Procedure 3: Rebuilding Read Models (Projections)

**Purpose:** Rebuild read models from event store after schema changes

**Risk Level:** Low (doesn't affect events)

**Downtime:** Zero (projections rebuild asynchronously)

#### Steps

1. **Clear Existing Read Model Data**

```sql
-- Connect to database
psql $DATABASE_URL

-- Clear read models (CAUTION: This deletes data that will be rebuilt)
TRUNCATE TABLE document_contents CASCADE;
TRUNCATE TABLE feedback_views CASCADE;
-- Note: document_views has foreign key constraints, handle carefully

-- Or for complete rebuild:
DROP TABLE IF EXISTS document_contents CASCADE;
DROP TABLE IF EXISTS document_views CASCADE;
DROP TABLE IF EXISTS feedback_views CASCADE;

-- Re-create tables from schema
\i docs/database/event_store_schema.sql
```

2. **Trigger Projection Rebuild**

```bash
# Option 1: Use projection admin API
curl -X POST https://api.example.com/api/v1/projection-admin/rebuild \
  -H "Content-Type: application/json" \
  -d '{"projection_name": "document"}'

# Option 2: Restart application (projections rebuild on startup)
sudo systemctl restart docsense
```

3. **Monitor Rebuild Progress**

```bash
# Watch logs
sudo journalctl -u docsense -f | grep -i projection

# Check projection lag
curl https://api.example.com/api/v1/projection-health

# Query read model counts
psql $DATABASE_URL -c "
  SELECT
    (SELECT COUNT(*) FROM events WHERE event_type LIKE 'Document%') as document_events,
    (SELECT COUNT(*) FROM document_views) as documents_projected,
    (SELECT COUNT(*) FROM events WHERE event_type LIKE 'Feedback%') as feedback_events,
    (SELECT COUNT(*) FROM feedback_views) as feedback_projected;
"
```

4. **Verify Projection Completion**

```bash
# Check all events processed
psql $DATABASE_URL -c "
  SELECT
    MAX(sequence) as last_event_sequence
  FROM events;
"

# Compare with projection checkpoint (if tracked)
# Projections are complete when they've processed all events
```

---

## Post-Migration Verification

### Verification Checklist

After any migration:

- [ ] **Schema correct** - `psql $DATABASE_URL -c "\d table_name"`
- [ ] **Indexes created** - `psql $DATABASE_URL -c "\di"`
- [ ] **Constraints valid** - `psql $DATABASE_URL -c "\d+ table_name"`
- [ ] **Event count unchanged** - `SELECT COUNT(*) FROM events`
- [ ] **Application starts** - `systemctl status docsense`
- [ ] **Health check passes** - `curl /api/v1/health`
- [ ] **Metrics available** - `curl /metrics`
- [ ] **No errors in logs** - `journalctl -u docsense --since "5 minutes ago"`
- [ ] **Read models populated** - Check document_views, feedback_views
- [ ] **End-to-end test** - Upload document, run analysis

### Automated Verification Script

```bash
#!/bin/bash
# verify-migration.sh

set -e

DATABASE_URL=$1
API_URL=${2:-"http://localhost:8000"}

echo "=== Database Verification ==="

# Check events table
echo -n "Events table... "
EVENT_COUNT=$(psql $DATABASE_URL -t -c "SELECT COUNT(*) FROM events;")
echo "✓ ($EVENT_COUNT events)"

# Check sequence column
echo -n "Sequence column... "
psql $DATABASE_URL -c "SELECT sequence FROM events LIMIT 1;" > /dev/null
echo "✓"

# Check semantic_ir table
echo -n "Semantic IR table... "
psql $DATABASE_URL -c "SELECT * FROM semantic_ir LIMIT 1;" > /dev/null
echo "✓"

echo ""
echo "=== Application Verification ==="

# Health check
echo -n "Health check... "
HEALTH=$(curl -s $API_URL/api/v1/health | jq -r '.status')
if [ "$HEALTH" = "healthy" ]; then
  echo "✓"
else
  echo "✗ (status: $HEALTH)"
  exit 1
fi

# Metrics
echo -n "Metrics endpoint... "
curl -s $API_URL/metrics | grep "http_requests_total" > /dev/null
echo "✓"

echo ""
echo "✅ All verifications passed!"
```

Usage:
```bash
chmod +x verify-migration.sh
./verify-migration.sh "$DATABASE_URL" "https://api.example.com"
```

---

## Rollback Procedures

### Rollback Strategy

**Event Store Changes:** Rollback using database restore

**Read Model Changes:** Drop tables and rebuild from events

**Event Schema Changes:** Deploy upcaster to handle old schema

### Rollback Scenario 1: Restore from Backup

```bash
# Stop application
sudo systemctl stop docsense

# Drop current database (DESTRUCTIVE!)
dropdb -U postgres docsense_prod

# Recreate database
createdb -U postgres docsense_prod

# Restore from backup
gunzip -c /backups/docsense_20251215_120000.sql.gz | psql $DATABASE_URL

# Or restore from S3
aws s3 cp s3://backups/docsense/docsense_20251215_120000.sql.gz - | gunzip | psql $DATABASE_URL

# Verify event count
psql $DATABASE_URL -c "SELECT COUNT(*) FROM events;"

# Start application
sudo systemctl start docsense
```

### Rollback Scenario 2: Remove Added Column

```sql
-- Connect to database
psql $DATABASE_URL

-- Drop column (CAUTION: This is irreversible!)
ALTER TABLE events DROP COLUMN IF EXISTS sequence;

-- Drop associated index
DROP INDEX IF EXISTS idx_events_sequence;

-- Verify
\d events
```

### Rollback Scenario 3: Remove Added Table

```sql
-- Drop table (CAUTION: This is irreversible!)
DROP TABLE IF EXISTS semantic_ir CASCADE;

-- Verify
\dt semantic_ir
```

---

## Common Migration Scenarios

### Scenario 1: Adding an Index

**Purpose:** Improve query performance

**Risk:** Low (non-blocking on PostgreSQL 11+)

**Procedure:**

```sql
-- Create index concurrently (no table lock)
CREATE INDEX CONCURRENTLY idx_document_views_status
ON document_views(status);

-- Verify index
\di idx_document_views_status

-- Check index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexname = 'idx_document_views_status';
```

### Scenario 2: Adding a Column to Read Model

**Purpose:** Add new field to projection

**Risk:** Low (doesn't affect events)

**Procedure:**

```sql
-- Add column with default value
ALTER TABLE document_views
ADD COLUMN new_field TEXT DEFAULT '';

-- Update column from events (rebuild projection)
-- This happens automatically when projection runs
```

### Scenario 3: Changing Event Schema

**Purpose:** Add field to event payload

**Risk:** Low (with upcaster)

**Procedure:**

1. Create event upcaster (see `/workspaces/src/infrastructure/persistence/event_upcaster.py`)
2. Deploy upcaster before changing event producer
3. Update event class to include new field
4. Deploy application

**Example Upcaster:**

```python
from src.infrastructure.persistence.event_upcaster import EventUpcaster

class DocumentUploadedV1ToV2Upcaster(EventUpcaster):
    def can_upcast(self, event_data: dict) -> bool:
        return (
            event_data.get("event_type") == "DocumentUploaded"
            and "new_field" not in event_data
        )

    def upcast(self, event_data: dict) -> dict:
        return {
            **event_data,
            "new_field": "default_value"
        }
```

---

## Troubleshooting

### Issue: Migration Script Fails

**Symptoms:** Python script exits with error

**Solutions:**

1. Check error message in output
2. Verify DATABASE_URL is correct
3. Check database connectivity: `psql $DATABASE_URL -c "SELECT 1;"`
4. Verify user has required permissions
5. Check disk space: `df -h`
6. Review script for syntax errors

### Issue: Application Won't Start After Migration

**Symptoms:** `systemctl status docsense` shows failed

**Solutions:**

1. Check logs: `journalctl -u docsense -n 100`
2. Verify schema changes applied correctly
3. Test database connection: `psql $DATABASE_URL`
4. Check for missing columns/tables application expects
5. Rollback if necessary

### Issue: Events Table Locked During Migration

**Symptoms:** Migration hangs, no progress

**Solutions:**

```sql
-- Find blocking queries
SELECT
  pid,
  usename,
  pg_blocking_pids(pid) as blocked_by,
  query as blocked_query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;

-- Terminate blocking query (CAUTION!)
SELECT pg_terminate_backend(pid);
```

### Issue: Foreign Key Constraint Violation

**Symptoms:** `ERROR: foreign key violation`

**Solutions:**

1. Check parent table has required rows
2. Verify foreign key references correct column
3. Add missing parent rows before migration
4. Use CASCADE on foreign key if appropriate

---

## Best Practices

1. **Always backup before migration**
2. **Test in staging first**
3. **Use idempotent scripts** (can run multiple times safely)
4. **Monitor during migration**
5. **Verify after migration**
6. **Document all changes**
7. **Never delete events** (immutability principle)
8. **Use event upcasting** for event schema evolution
9. **Rebuild read models** from events when needed
10. **Schedule maintenance windows** for risky migrations

---

## References

- [Event Store Schema](/workspaces/docs/database/event_store_schema.sql)
- [Migration Scripts](/workspaces/scripts/)
- [ADR-001: DDD with Event Sourcing and CQRS](/workspaces/docs/decisions/001-use-ddd-event-sourcing-cqrs.md)
- [Production Deployment Guide](production-deployment-guide.md)
- [Environment Variables](environment-variables.md)
