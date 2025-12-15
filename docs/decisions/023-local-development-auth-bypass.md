# ADR-023: Local Development Authentication Bypass Mode

**Status**: Accepted  
**Date**: 2024-12-15  
**Decision Makers**: Engineering Team  
**Priority**: Medium  
**Impact**: Developer Experience, Testing

---

## Context

Currently, local development requires setting up Kerberos authentication headers or running behind an authentication proxy. This creates friction for developers who want to:

1. **Quick Testing**: Start the application and immediately test features
2. **Integration Tests**: Run E2E tests without authentication infrastructure
3. **Demo Mode**: Show functionality to stakeholders without auth setup
4. **Isolated Development**: Work on features unrelated to authentication

### Current Pain Points

- Cannot access the application without X-User-Kerberos header
- Integration tests require complex auth mocking
- New developers face authentication setup as first barrier
- Local testing of document features requires manual header injection

### Requirements

- **Zero Friction**: Should work out-of-the-box in local development
- **Safe**: Must be disabled in production environments
- **Configurable**: Easy to enable/disable via environment variable
- **Test User**: Predictable test user with test documents
- **Audit Compliance**: All actions still logged with test user ID

---

## Decision

We will implement a **development-mode authentication bypass** that creates a test user with pre-seeded test documents when `ENVIRONMENT=development` and `DEV_AUTH_BYPASS=true`.

### 1. Configuration

**New Environment Variables**:

```bash
# Enable auth bypass for local development
ENVIRONMENT=development
DEV_AUTH_BYPASS=true  # Default: false

# Optional: Customize test user
DEV_TEST_USER_KERBEROS=testuser  # Default: "testuser"
DEV_TEST_USER_NAME="Test User"   # Default: "Test User"
DEV_TEST_USER_EMAIL=test@local.dev  # Default: "testuser@local.dev"
DEV_TEST_USER_GROUPS=testing,dev  # Default: "testing"
```

**Safety Checks**:
- Only enabled when `ENVIRONMENT=development`
- Logs warning on startup when bypass is active
- Returns 403 if attempted in production
- Header in API responses indicates bypass mode: `X-Dev-Mode: enabled`

### 2. Implementation

**Middleware Modification** (`src/api/middleware/auth.py`):

```python
class KerberosAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for Kerberos authentication.
    
    In production: Validates X-User-Kerberos header
    In development (bypass enabled): Injects test user if no header present
    """
    
    async def dispatch(self, request: Request, call_next):
        # Production mode: Strict authentication required
        if settings.ENVIRONMENT == "production":
            kerberos_id = request.headers.get("X-User-Kerberos")
            if not kerberos_id:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required"}
                )
            # Validate and set request state
            request.state.kerberos_id = kerberos_id
            # ... extract groups, etc.
        
        # Development mode with bypass enabled
        elif settings.DEV_AUTH_BYPASS:
            kerberos_id = request.headers.get("X-User-Kerberos")
            
            # If no header, inject test user
            if not kerberos_id:
                logger.info("DEV MODE: Using test user (no auth header)")
                request.state.kerberos_id = settings.DEV_TEST_USER_KERBEROS
                request.state.user_groups = set(settings.DEV_TEST_USER_GROUPS.split(','))
                request.state.display_name = settings.DEV_TEST_USER_NAME
                request.state.email = settings.DEV_TEST_USER_EMAIL
                request.state.dev_mode = True
            else:
                # Header provided: use that user
                request.state.kerberos_id = kerberos_id
                request.state.user_groups = set(request.headers.get("X-User-Groups", "").split(','))
                request.state.display_name = kerberos_id
                request.state.email = f"{kerberos_id}@local.dev"
                request.state.dev_mode = True
        
        # Development mode without bypass: require headers like production
        else:
            kerberos_id = request.headers.get("X-User-Kerberos")
            if not kerberos_id:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required. Set DEV_AUTH_BYPASS=true for test user."}
                )
            request.state.kerberos_id = kerberos_id
        
        response = await call_next(request)
        
        # Add dev mode indicator header
        if getattr(request.state, "dev_mode", False):
            response.headers["X-Dev-Mode"] = "enabled"
            response.headers["X-Dev-User"] = request.state.kerberos_id
        
        return response
```

### 3. Test Data Seeding

**Startup Data Loader** (`src/infrastructure/dev/test_data_loader.py`):

```python
class TestDataLoader:
    """Loads test documents for development mode."""
    
    async def load_test_data(self, user_kerberos_id: str):
        """
        Load test documents for the test user.
        
        Creates 5-10 sample documents covering various scenarios:
        - Clean document (all requirements met)
        - Missing sections (appendix, governance)
        - Incomplete formulas
        - External dependencies
        - Ambiguous parameters
        """
        
        test_documents = [
            {
                "filename": "test_01_clean.pdf",
                "title": "Simple Interest Calculation - Clean",
                "description": "Well-documented algorithm with all sections",
                "path": "data/test_documents/doc_01_clean.json"
            },
            {
                "filename": "test_02_missing_appendix.pdf",
                "title": "Bond Pricing - Missing Appendix",
                "description": "Missing data sources appendix",
                "path": "data/test_documents/doc_02_missing_appendix.json"
            },
            # ... more test docs
        ]
        
        for doc_data in test_documents:
            # Load from test_documents directory
            # Upload as test user
            # Mark with special metadata: {"dev_test_data": True}
            pass
```

**Integration in Application Startup** (`src/api/main.py`):

```python
@app.on_event("startup")
async def startup_event():
    """Application startup."""
    
    # Standard initialization
    await Container.get_instance()
    
    # Development mode: Load test data
    if settings.ENVIRONMENT == "development" and settings.DEV_AUTH_BYPASS:
        logger.warning("=" * 60)
        logger.warning("🚨 DEVELOPMENT MODE: Auth bypass enabled")
        logger.warning(f"   Test User: {settings.DEV_TEST_USER_KERBEROS}")
        logger.warning(f"   Groups: {settings.DEV_TEST_USER_GROUPS}")
        logger.warning("   All requests without auth headers use test user")
        logger.warning("=" * 60)
        
        # Load test documents (if not already loaded)
        test_loader = TestDataLoader()
        await test_loader.ensure_test_data_loaded(
            user_kerberos_id=settings.DEV_TEST_USER_KERBEROS
        )
```

### 4. Frontend Integration

**API Client Auto-Configuration** (`client/src/lib/api.ts`):

```typescript
// Auto-detect dev mode from backend
const checkDevMode = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/v1/health');
    return response.headers.get('X-Dev-Mode') === 'enabled';
  } catch {
    return false;
  }
};

// Show dev mode banner
if (await checkDevMode()) {
  console.log('🚨 Development Mode: Using test user');
  // Optional: Show banner in UI
}
```

**Dev Mode Banner Component** (`client/src/components/DevModeBanner.tsx`):

```tsx
export function DevModeBanner() {
  const [devMode, setDevMode] = useState(false);
  
  useEffect(() => {
    // Check if backend is in dev mode
    fetch('/api/v1/health')
      .then(res => setDevMode(res.headers.get('X-Dev-Mode') === 'enabled'));
  }, []);
  
  if (!devMode) return null;
  
  return (
    <div className="bg-yellow-100 border-b border-yellow-300 px-4 py-2 text-sm">
      <span className="font-semibold">🚨 Development Mode</span>
      {' - '}
      <span>Authenticated as test user with sample documents</span>
    </div>
  );
}
```

---

## Configuration

**Environment File** (`.env.local` example):

```bash
# Database
DATABASE_URL=postgresql://docsense:docsense_local_dev@localhost:5432/docsense

# AI Provider (at least one required)
ANTHROPIC_API_KEY=your_key_here

# Development Mode
ENVIRONMENT=development
DEV_AUTH_BYPASS=true

# Optional: Custom test user
DEV_TEST_USER_KERBEROS=testuser
DEV_TEST_USER_NAME="Test User"
DEV_TEST_USER_EMAIL=test@local.dev
DEV_TEST_USER_GROUPS=testing,dev
```

---

## Usage

### Starting the Application

```bash
# 1. Set environment
export ENVIRONMENT=development
export DEV_AUTH_BYPASS=true

# 2. Start services
./start-all.sh

# 3. Access application
open http://localhost:5000
# Automatically logged in as test user
# See sample documents pre-loaded
```

### Testing with Different Users

```bash
# Override test user via header (even with bypass enabled)
curl -H "X-User-Kerberos: jsmith" \
     -H "X-User-Groups: equity-trading" \
     http://localhost:8000/api/v1/auth/me
```

### Integration Tests

```python
# Tests automatically use test user in dev mode
def test_document_upload():
    response = client.post("/api/v1/documents", 
        files={"file": open("test.pdf", "rb")})
    # No auth headers needed - uses dev bypass
    assert response.status_code == 200
```

---

## Security Considerations

### Production Safety

1. **Environment Check**: Bypass only works when `ENVIRONMENT=development`
2. **Explicit Opt-In**: Requires `DEV_AUTH_BYPASS=true` (default: false)
3. **Logging**: Warns loudly on startup when bypass is enabled
4. **Headers**: Responses include `X-Dev-Mode: enabled` header
5. **No Production Data**: Test user only has access to test documents

### Audit Trail

Even in development mode:
- All actions logged with test user ID
- Events stored in event store
- Full audit trail maintained
- Test data clearly marked in metadata

---

## Consequences

### Positive

✅ **Zero Setup**: Works immediately for new developers  
✅ **Fast Testing**: No auth infrastructure needed  
✅ **Integration Tests**: Simpler test setup  
✅ **Demos**: Easy stakeholder demonstrations  
✅ **Isolated Testing**: Test document features without auth complexity  

### Negative

❌ **Not Production-Like**: Auth flow differs from production  
❌ **Security Awareness**: Developers might forget to test auth  
❌ **Environment Config**: Must remember to set ENVIRONMENT correctly  

### Mitigation

- Clear documentation on production vs dev auth
- CI/CD tests run with auth headers (production-like)
- Startup warning makes dev mode obvious
- Separate integration tests for auth flows

---

## Implementation Checklist

- [ ] Add `DEV_AUTH_BYPASS` configuration to Settings
- [ ] Modify KerberosAuthMiddleware with bypass logic
- [ ] Create TestDataLoader for sample documents
- [ ] Integrate test data loading in startup
- [ ] Add dev mode detection to frontend
- [ ] Create DevModeBanner component
- [ ] Update README with dev mode instructions
- [ ] Add integration tests for dev mode
- [ ] Document security considerations

---

## Related

- **ADR-021**: User and Group Authentication & Authorization
- **ADR-012**: Doppler Secret Management
- **Implementation Plan**: Phase 13 (Authentication)

---

## References

- FastAPI Middleware: https://fastapi.tiangolo.com/advanced/middleware/
- Environment-Based Configuration: Best Practices
- Development Mode Patterns: Rails, Django examples
