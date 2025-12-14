# ADR-021: User and Group Authentication & Authorization

**Status**: Proposed  
**Date**: 2024-12-14  
**Decision Makers**: Engineering Team  
**Priority**: High  
**Impact**: Architecture, Security, Database

---

## Context

The application currently lacks user authentication and authorization mechanisms. All documents are globally accessible without user-specific access control. We need to implement:

1. **User Identification**: Kerberos-based authentication (6-character string identifiers)
2. **Group-Based Access**: Users belong to groups (longer string identifiers)
3. **Document Ownership**: Documents owned by uploading user
4. **Sharing Control**: Optional group-level document visibility
5. **Role-Based Access Control (RBAC)**: Best practices for authorization
6. **Single Database**: Unified database for development and production environments

### Business Requirements

- **Privacy by Default**: Documents private to owner unless explicitly shared
- **Group Collaboration**: Users can share documents with their group
- **Kerberos Integration**: Leverage existing enterprise authentication
- **Audit Trail**: All access and sharing actions must be logged
- **Future-Ready**: Architecture supports future multi-tenancy needs

### Technical Constraints

- Must maintain event sourcing and CQRS patterns
- Single PostgreSQL database for both environments
- Minimal disruption to existing domain model
- Support for future OAuth2/OIDC migration
- Performance: Sub-100ms authorization checks

---

## Decision

We will implement a **multi-layered authentication and authorization architecture** with the following components:

### 1. Authentication Layer

**Kerberos Integration via HTTP Headers**

```python
# Authentication flow:
# 1. Client authenticates with Kerberos/AD
# 2. Authentication proxy injects headers:
#    - X-User-Kerberos: 6-character username (e.g., "jsmith")
#    - X-User-Groups: comma-separated group list (e.g., "equity-trading,risk-management")
# 3. FastAPI middleware validates and extracts user context
```

**Why Kerberos Headers**:
- Leverages existing enterprise authentication infrastructure
- No password management in application
- Single Sign-On (SSO) experience
- Authentication handled at infrastructure layer
- Application focuses on authorization logic

### 2. Domain Model: User and Group Entities

**New Domain Aggregates**:

```python
# src/domain/aggregates/user.py
class User(Aggregate):
    """
    User aggregate - represents authenticated application user.
    
    Properties:
    - kerberos_id: str (6-char, primary identifier)
    - display_name: str (optional, for UI)
    - email: str (optional)
    - groups: List[str] (group memberships)
    - roles: List[UserRole] (application-level roles)
    - is_active: bool
    - created_at: datetime
    - last_login: datetime
    """

# src/domain/value_objects/user_role.py
class UserRole(Enum):
    """Application-level roles for RBAC."""
    VIEWER = "viewer"           # Can view own and shared documents
    CONTRIBUTOR = "contributor" # Can create, edit, share documents
    ADMIN = "admin"            # Full access, user management
    AUDITOR = "auditor"        # Read-only access to all documents + audit logs
```

**Group Entity (Value Object)**:

```python
# src/domain/value_objects/group.py
@dataclass(frozen=True)
class Group:
    """
    Group value object - represents organizational unit.
    
    Properties:
    - id: str (e.g., "equity-trading", "risk-management")
    - display_name: str (e.g., "Equity Trading Team")
    - description: str (optional)
    """
    id: str
    display_name: str
    description: Optional[str] = None
    
    def __post_init__(self):
        if not self.id or len(self.id) < 3:
            raise ValueError("Group ID must be at least 3 characters")
```

### 3. Document Access Control

**Enhanced Document Aggregate**:

```python
# Modifications to src/domain/aggregates/document.py
class Document(Aggregate):
    def __init__(self, document_id: UUID):
        super().__init__(document_id)
        # NEW PROPERTIES:
        self._owner_kerberos_id: str = ""
        self._visibility: DocumentVisibility = DocumentVisibility.PRIVATE
        self._shared_with_groups: List[str] = []
        self._access_grants: List[AccessGrant] = []  # Future: individual user grants

# src/domain/value_objects/document_visibility.py
class DocumentVisibility(Enum):
    """Document visibility level."""
    PRIVATE = "private"         # Owner only
    GROUP = "group"            # Owner + all group members
    ORGANIZATION = "organization"  # All authenticated users (future)
    PUBLIC = "public"          # Unauthenticated access (future)
```

**New Domain Events**:

```python
# src/domain/events/document_events.py

@dataclass
class DocumentSharedWithGroup(DomainEvent):
    """Document visibility changed to group-level."""
    aggregate_id: UUID
    group_id: str
    shared_by_kerberos_id: str
    visibility: str  # "group"
    
@dataclass
class DocumentMadePrivate(DomainEvent):
    """Document visibility changed to private."""
    aggregate_id: UUID
    changed_by_kerberos_id: str
    visibility: str  # "private"

@dataclass
class DocumentAccessGranted(DomainEvent):
    """Individual access grant (future feature)."""
    aggregate_id: UUID
    granted_to_kerberos_id: str
    granted_by_kerberos_id: str
    permission_level: str  # "read", "write", "admin"
```

### 4. Authorization Service

**Centralized Authorization Logic**:

```python
# src/domain/services/authorization_service.py
class AuthorizationService:
    """
    Centralized authorization decisions.
    Implements Policy-Based Access Control (PBAC).
    """
    
    def can_view_document(
        self,
        user: User,
        document: Document
    ) -> bool:
        """Check if user can view document."""
        # Owner can always view
        if document.owner_kerberos_id == user.kerberos_id:
            return True
        
        # Admin/Auditor can view all
        if UserRole.ADMIN in user.roles or UserRole.AUDITOR in user.roles:
            return True
        
        # Group sharing
        if document.visibility == DocumentVisibility.GROUP:
            user_groups = set(user.groups)
            doc_groups = set(document.shared_with_groups)
            if user_groups & doc_groups:  # Intersection
                return True
        
        # Individual grants (future)
        for grant in document.access_grants:
            if grant.user_kerberos_id == user.kerberos_id:
                return True
        
        return False
    
    def can_edit_document(
        self,
        user: User,
        document: Document
    ) -> bool:
        """Check if user can edit document."""
        # Only owner and admins can edit
        if document.owner_kerberos_id == user.kerberos_id:
            return True
        
        if UserRole.ADMIN in user.roles:
            return True
        
        return False
    
    def can_share_document(
        self,
        user: User,
        document: Document
    ) -> bool:
        """Check if user can change document sharing."""
        # Only owner and admins can share
        return self.can_edit_document(user, document)
    
    def can_delete_document(
        self,
        user: User,
        document: Document
    ) -> bool:
        """Check if user can delete document."""
        # Only owner and admins can delete
        return self.can_edit_document(user, document)
```

### 5. Database Schema Changes

**New Tables**:

```sql
-- User management table (read model)
CREATE TABLE users (
    kerberos_id VARCHAR(6) PRIMARY KEY,
    display_name VARCHAR(255),
    email VARCHAR(255),
    groups TEXT[] DEFAULT '{}',  -- Array of group IDs
    roles TEXT[] DEFAULT '{}',   -- Array of role names
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_groups ON users USING GIN(groups);
CREATE INDEX idx_users_is_active ON users(is_active);

-- Group definitions table
CREATE TABLE groups (
    id VARCHAR(255) PRIMARY KEY,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_groups_is_active ON groups(is_active);

-- Document access control (read model)
ALTER TABLE document_views ADD COLUMN owner_kerberos_id VARCHAR(6) NOT NULL DEFAULT 'system';
ALTER TABLE document_views ADD COLUMN visibility VARCHAR(20) NOT NULL DEFAULT 'private';
ALTER TABLE document_views ADD COLUMN shared_with_groups TEXT[] DEFAULT '{}';

CREATE INDEX idx_document_views_owner ON document_views(owner_kerberos_id);
CREATE INDEX idx_document_views_visibility ON document_views(visibility);
CREATE INDEX idx_document_views_shared_groups ON document_views USING GIN(shared_with_groups);

-- Access audit log
CREATE TABLE access_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_kerberos_id VARCHAR(6) NOT NULL,
    document_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,  -- 'view', 'edit', 'share', 'delete', 'download'
    result VARCHAR(20) NOT NULL,  -- 'granted', 'denied'
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_access_audit_user ON access_audit_log(user_kerberos_id);
CREATE INDEX idx_access_audit_document ON access_audit_log(document_id);
CREATE INDEX idx_access_audit_created ON access_audit_log(created_at);
CREATE INDEX idx_access_audit_action ON access_audit_log(action);
```

**Event Store Changes**:

```sql
-- Update events table to track user context
ALTER TABLE events ADD COLUMN user_kerberos_id VARCHAR(6);
ALTER TABLE events ADD COLUMN user_groups TEXT[];

CREATE INDEX idx_events_user ON events(user_kerberos_id);
```

### 6. API Layer Changes

**FastAPI Dependency for Authentication**:

```python
# src/api/dependencies/auth.py
from fastapi import Header, HTTPException, Depends
from typing import Optional

class CurrentUser:
    """Current authenticated user context."""
    def __init__(
        self,
        kerberos_id: str,
        groups: List[str],
        roles: List[UserRole]
    ):
        self.kerberos_id = kerberos_id
        self.groups = groups
        self.roles = roles

async def get_current_user(
    x_user_kerberos: str = Header(..., description="Kerberos username"),
    x_user_groups: Optional[str] = Header(None, description="Comma-separated groups")
) -> CurrentUser:
    """
    Extract current user from headers injected by auth proxy.
    
    Raises:
        HTTPException: 401 if authentication headers missing or invalid
    """
    if not x_user_kerberos or len(x_user_kerberos) != 6:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing Kerberos authentication"
        )
    
    # Parse groups
    groups = []
    if x_user_groups:
        groups = [g.strip() for g in x_user_groups.split(",")]
    
    # Get user from repository (creates if first login)
    user = await user_repository.get_or_create(
        kerberos_id=x_user_kerberos,
        groups=groups
    )
    
    return CurrentUser(
        kerberos_id=user.kerberos_id,
        groups=user.groups,
        roles=user.roles
    )

async def require_role(*required_roles: UserRole):
    """Dependency to require specific role(s)."""
    async def check_role(user: CurrentUser = Depends(get_current_user)):
        if not any(role in user.roles for role in required_roles):
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of: {', '.join(r.value for r in required_roles)}"
            )
        return user
    return check_role
```

**Updated API Endpoints**:

```python
# src/api/routes/documents.py

@router.post("/documents")
async def upload_document(
    file: UploadFile,
    user: CurrentUser = Depends(get_current_user)
):
    """Upload document - automatically owned by current user."""
    command = UploadDocument(
        document_id=uuid4(),
        filename=file.filename,
        content=await file.read(),
        uploaded_by=user.kerberos_id  # Set owner
    )
    # ... existing logic

@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user)
):
    """Get document - checks authorization."""
    document = await document_repository.get(document_id)
    
    # Authorization check
    if not authorization_service.can_view_document(user, document):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this document"
        )
    
    return document

@router.patch("/documents/{document_id}/sharing")
async def update_document_sharing(
    document_id: UUID,
    visibility: DocumentVisibility,
    user: CurrentUser = Depends(get_current_user)
):
    """Update document sharing settings."""
    document = await document_repository.get(document_id)
    
    # Authorization check
    if not authorization_service.can_share_document(user, document):
        raise HTTPException(status_code=403, detail="Cannot share document")
    
    # Apply sharing change
    if visibility == DocumentVisibility.GROUP:
        document.share_with_groups(user.groups, user.kerberos_id)
    else:
        document.make_private(user.kerberos_id)
    
    await document_repository.save(document)
    return {"status": "updated"}

@router.get("/documents")
async def list_documents(
    user: CurrentUser = Depends(get_current_user),
    include_shared: bool = True
):
    """List documents accessible to user."""
    # Query documents where:
    # - owner = user, OR
    # - visibility = 'group' AND shared_with_groups overlaps user.groups
    documents = await document_repository.find_accessible_by_user(
        user_kerberos_id=user.kerberos_id,
        user_groups=user.groups,
        include_shared=include_shared
    )
    return documents
```

### 7. Frontend Changes

**Authentication Context**:

```typescript
// client/src/contexts/AuthContext.tsx
interface User {
  kerberosId: string;
  displayName?: string;
  groups: string[];
  roles: UserRole[];
}

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// HTTP interceptor to ensure headers present
axios.interceptors.request.use((config) => {
  // Headers should be injected by auth proxy
  // Frontend just validates they exist
  if (!config.headers['X-User-Kerberos']) {
    throw new Error('Authentication required');
  }
  return config;
});
```

**Sharing Toggle Component**:

```typescript
// client/src/components/DocumentSharingToggle.tsx
interface Props {
  documentId: string;
  currentVisibility: 'private' | 'group';
  onUpdate: (visibility: string) => void;
}

export function DocumentSharingToggle({ documentId, currentVisibility, onUpdate }: Props) {
  const handleToggle = async (checked: boolean) => {
    const newVisibility = checked ? 'group' : 'private';
    await api.patch(`/documents/${documentId}/sharing`, {
      visibility: newVisibility
    });
    onUpdate(newVisibility);
  };

  return (
    <Switch
      checked={currentVisibility === 'group'}
      onCheckedChange={handleToggle}
      label="Share with my groups"
      description="Make visible to all members of your groups"
    />
  );
}
```

### 8. Security Considerations

**Defense in Depth**:

1. **Authentication Proxy**: External (nginx, Apache, Azure App Proxy)
2. **Header Validation**: Middleware validates required headers present
3. **Authorization Service**: Domain-level permission checks
4. **Database Constraints**: Row-level security policies (future)
5. **Audit Logging**: All access attempts logged

**Security Best Practices**:

- **No Password Storage**: Delegated to Kerberos/AD
- **Least Privilege**: Users start with VIEWER role
- **Fail Secure**: Authorization checks default to deny
- **Audit Everything**: All access and sharing events logged
- **Input Validation**: Kerberos IDs validated (6 chars, alphanumeric)
- **SQL Injection Prevention**: Parameterized queries only
- **XSS Prevention**: Content Security Policy headers

**Future Enhancements**:

```python
# Row-Level Security (RLS) in PostgreSQL
CREATE POLICY document_access_policy ON document_views
    FOR SELECT
    USING (
        owner_kerberos_id = current_setting('app.current_user')::VARCHAR
        OR 
        visibility = 'group' AND shared_with_groups && 
            string_to_array(current_setting('app.user_groups'), ',')
    );
```

---

## Consequences

### Positive

✅ **Security**: Strong authentication via Kerberos, granular authorization  
✅ **Privacy**: Documents private by default, explicit sharing required  
✅ **Audit Trail**: Complete logging of access and sharing  
✅ **Scalability**: Authorization service can be cached/optimized  
✅ **User Experience**: Simple sharing toggle, SSO integration  
✅ **Maintainability**: Clear separation of authentication vs authorization  
✅ **Event Sourcing Preserved**: All access changes are domain events  
✅ **Future-Proof**: Architecture supports OAuth2/OIDC migration

### Negative

⚠️ **Migration Complexity**: Existing documents need owner assignment  
⚠️ **Authentication Dependency**: Requires auth proxy infrastructure  
⚠️ **Query Complexity**: Document lists require permission filtering  
⚠️ **Testing Overhead**: Mocking authentication for tests  
⚠️ **Performance**: Authorization checks add latency (mitigated via caching)

### Mitigation Strategies

1. **Migration Script**: Assign existing documents to "system" user, bulk reassignment tool
2. **Development Auth**: Mock auth middleware for local development
3. **Query Optimization**: Database indexes on owner + shared_with_groups
4. **Caching**: Redis cache for user permissions (5-minute TTL)
5. **Performance Testing**: Load test authorization service under realistic traffic

---

## Implementation Notes

### Phase 1: Foundation (Week 1)

1. Database schema migration (users, groups, access_audit_log tables)
2. User and Group domain entities
3. Updated DocumentUploaded event with owner_kerberos_id
4. Migration script for existing documents

### Phase 2: Authorization (Week 2)

1. AuthorizationService implementation
2. DocumentVisibility value object
3. Document sharing events and methods
4. Unit tests for authorization logic

### Phase 3: API Integration (Week 3)

1. FastAPI authentication middleware
2. get_current_user dependency
3. Updated document endpoints with auth checks
4. Access audit logging middleware

### Phase 4: Frontend (Week 4)

1. AuthContext and authentication state
2. Sharing toggle component
3. Document list filtering by permissions
4. User feedback for permission errors

### Phase 5: Production Hardening (Week 5)

1. Integration tests with mock authentication
2. Performance testing and optimization
3. Security audit
4. Documentation and runbooks

---

## Alternatives Considered

### Alternative 1: JWT-Based Authentication

**Rejected**: Adds complexity of token management, rotation, validation. Kerberos headers simpler for enterprise environment with existing SSO.

### Alternative 2: Database-Level RLS Only

**Rejected**: Less flexible for complex authorization logic. Application-level authorization provides better auditability and testability.

### Alternative 3: Separate Multi-Tenant Architecture

**Rejected**: Over-engineered for current needs. Group-based sharing provides sufficient isolation without multi-tenant complexity.

### Alternative 4: OAuth2/OIDC

**Deferred**: More complex to implement initially. Architecture supports future migration. Kerberos meets current enterprise requirements.

---

## References

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **NIST Access Control Guidelines**: NIST SP 800-162
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
- **PostgreSQL Row-Level Security**: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- **Domain-Driven Design**: Eric Evans, Chapter on "Bounded Contexts and Integration"
- **ADR-001**: DDD/Event Sourcing/CQRS patterns (maintained)

---

## Status History

- **2024-12-14**: Proposed - Initial architecture design
