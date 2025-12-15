# Authentication Migration Guide

**Version**: 1.0  
**Date**: December 15, 2025  
**Applies to**: Phase 13 (Authentication & Authorization)

## Overview

Phase 13 introduces user authentication, document ownership, and access control. This guide helps you migrate from a pre-authentication deployment to the new authenticated system.

## Prerequisites

- Existing DocSense deployment (pre-Phase 13)
- PostgreSQL database access
- Kerberos authentication infrastructure (or test headers for development)

## Migration Steps

### 1. Database Migrations

Run the Phase 13 database migrations in order:

```bash
# Connect to your database
psql $DATABASE_URL

# Run migrations
\i scripts/migrations/013_create_users_table.sql
\i scripts/migrations/014_create_user_groups_table.sql
\i scripts/migrations/015_add_document_ownership.sql
\i scripts/migrations/016_create_access_audit_log.sql
```

**What this does:**
- Creates `users` table for user profiles
- Creates `user_groups` table for group memberships
- Adds `owner_kerberos_id`, `visibility`, `shared_with_groups` to documents
- Creates `access_audit_log` for security audit trail

### 2. Migrate Existing Documents

Existing documents need to be assigned an owner. Choose one approach:

#### Option A: Assign to System User (Recommended)

```sql
-- Update all documents without owner to system user
UPDATE document_projections 
SET owner_kerberos_id = 'system'
WHERE owner_kerberos_id IS NULL;

-- Create system user if needed
INSERT INTO users (id, kerberos_id, display_name, email, roles, is_active)
VALUES (
    gen_random_uuid(),
    'system',
    'System',
    'system@example.com',
    ARRAY['ADMIN']::varchar[],
    true
)
ON CONFLICT (kerberos_id) DO NOTHING;
```

#### Option B: Assign to Admin User

```sql
-- Replace 'admin-user' with actual admin Kerberos ID
UPDATE document_projections 
SET owner_kerberos_id = 'admin-user'
WHERE owner_kerberos_id IS NULL;
```

### 3. Configure Authentication Headers

Update your reverse proxy or API gateway to forward Kerberos headers.

#### Nginx Example

```nginx
location /api/ {
    proxy_pass http://docsense-backend:8000;
    
    # Forward Kerberos authentication headers
    proxy_set_header X-User-Kerberos $remote_user;
    proxy_set_header X-User-Groups $http_x_user_groups;
    proxy_set_header Host $host;
}
```

#### Apache Example

```apache
<Location /api/>
    ProxyPass http://docsense-backend:8000/
    
    # Forward Kerberos authentication headers
    RequestHeader set X-User-Kerberos %{REMOTE_USER}e
    RequestHeader set X-User-Groups %{HTTP_X_USER_GROUPS}e
</Location>
```

#### Development/Testing (No Kerberos)

For development without Kerberos, use test headers:

```bash
curl -H "X-User-Kerberos: testuser" \
     -H "X-User-Groups: finance,trading" \
     http://localhost:8000/api/v1/auth/me
```

### 4. Update Environment Variables

No new environment variables are required! Authentication uses:
- Existing `DATABASE_URL` for user storage
- HTTP headers (`X-User-Kerberos`, `X-User-Groups`) for authentication

### 5. Test Authentication

#### Verify User Auto-Registration

```bash
# Access any endpoint - user will be auto-registered
curl -H "X-User-Kerberos: alice" \
     -H "X-User-Groups: finance" \
     http://localhost:8000/api/v1/auth/me

# Expected response:
{
  "kerberos_id": "alice",
  "display_name": "alice",
  "email": "alice@example.com",
  "groups": ["finance"],
  "roles": ["VIEWER"],
  "permissions": ["documents:read"],
  "is_active": true
}
```

#### Verify Document Ownership

```bash
# Upload a document - owner will be set automatically
curl -H "X-User-Kerberos: bob" \
     -F "file=@strategy.pdf" \
     http://localhost:8000/api/v1/documents

# Check ownership in response
{
  "id": "...",
  "title": "Strategy Document",
  "owner_kerberos_id": "bob",  # Auto-set
  "visibility": "private",      # Default
  "shared_with_groups": []
}
```

#### Verify Authorization

```bash
# Try to access someone else's private document (should fail)
curl -H "X-User-Kerberos: alice" \
     http://localhost:8000/api/v1/documents/{bob-document-id}

# Expected: 403 Forbidden

# Share document with alice's group
curl -H "X-User-Kerberos: bob" \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"groups": ["finance"]}' \
     http://localhost:8000/api/v1/documents/{document-id}/share

# Now alice can access it
curl -H "X-User-Kerberos: alice" \
     -H "X-User-Groups: finance" \
     http://localhost:8000/api/v1/documents/{document-id}
```

### 6. Verify Audit Logging

```sql
-- Check audit log is capturing access
SELECT 
    user_kerberos_id,
    action,
    result,
    occurred_at
FROM access_audit_log
ORDER BY occurred_at DESC
LIMIT 10;
```

Expected output:
```
 user_kerberos_id | action | result  | occurred_at
------------------+--------+---------+-------------------------
 alice            | view   | allowed | 2025-12-15 10:30:00
 bob              | share  | allowed | 2025-12-15 10:25:00
 alice            | view   | denied  | 2025-12-15 10:20:00
```

## Frontend Updates

If you have a custom frontend, update it to:

1. **Display current user** - Call `GET /api/v1/auth/me`
2. **Show sharing options** - Use `POST /api/v1/documents/{id}/share`
3. **Show ownership** - Display `owner_kerberos_id` in document list

The reference React frontend already includes these features.

## Rollback Procedure

If you need to rollback:

```sql
-- 1. Drop new tables (loses user/audit data)
DROP TABLE IF EXISTS access_audit_log;
DROP TABLE IF EXISTS user_groups;
DROP TABLE IF EXISTS users;

-- 2. Remove document ownership columns
ALTER TABLE document_projections 
DROP COLUMN IF EXISTS owner_kerberos_id,
DROP COLUMN IF EXISTS visibility,
DROP COLUMN IF EXISTS shared_with_groups;

-- 3. Redeploy pre-Phase 13 version
```

⚠️ **Warning**: Rollback loses all user data and audit logs!

## Troubleshooting

### Issue: "Field required" error on startup

**Cause**: Missing `DATABASE_URL`

**Solution**: 
```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/docsense"
```

### Issue: 401 Unauthorized on all requests

**Cause**: Missing authentication headers

**Solution**: Check reverse proxy forwards `X-User-Kerberos` header

### Issue: Users auto-registered but cannot access documents

**Cause**: New users get `VIEWER` role by default, cannot create documents

**Solution**: Assign `CONTRIBUTOR` role:
```sql
UPDATE users 
SET roles = ARRAY['CONTRIBUTOR']::varchar[]
WHERE kerberos_id = 'alice';
```

### Issue: Admin cannot access all documents

**Cause**: Need to grant `ADMIN` role

**Solution**:
```sql
UPDATE users 
SET roles = ARRAY['ADMIN']::varchar[]
WHERE kerberos_id = 'admin-user';
```

## Security Considerations

1. **Audit Logs**: Review access patterns regularly
   ```sql
   -- Find denied access attempts
   SELECT * FROM access_audit_log 
   WHERE result = 'denied' 
   ORDER BY occurred_at DESC;
   ```

2. **Orphaned Documents**: Check for documents without owners
   ```sql
   SELECT id, title, created_at 
   FROM document_projections 
   WHERE owner_kerberos_id IS NULL;
   ```

3. **Inactive Users**: Periodically review and deactivate
   ```sql
   -- Deactivate users inactive for 90 days
   UPDATE users 
   SET is_active = false 
   WHERE last_login < NOW() - INTERVAL '90 days';
   ```

## Support

For issues or questions:
- Review [ADR-021](../decisions/021-user-group-authentication-authorization.md)
- Check application logs for authentication errors
- Run Phase 13 tests: `pytest tests/unit/domain/aggregates/test_user.py`

## Validation Checklist

After migration, verify:

- [ ] All database migrations applied successfully
- [ ] Existing documents have owners assigned
- [ ] Authentication headers forwarded correctly
- [ ] Users auto-register on first access
- [ ] Document ownership and sharing work
- [ ] Audit log captures all access attempts
- [ ] Authorization checks prevent unauthorized access
- [ ] Frontend displays user info and sharing options
- [ ] All 80 Phase 13 tests pass

## Next Steps

After successful migration:
1. Train users on document sharing features
2. Define group structure for your organization
3. Assign appropriate roles to users (ADMIN, CONTRIBUTOR, VIEWER, AUDITOR)
4. Set up regular audit log reviews
5. Document your organization's access control policies
