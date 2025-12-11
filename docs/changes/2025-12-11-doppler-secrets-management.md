# Change Log: Doppler Secrets Management Integration

## Date
2025-12-11

## Author
AI Agent

## Summary

Integrated Doppler as the centralized secrets management solution. Only a single `DOPPLER_TOKEN` is stored in Replit, with all other secrets (API keys, session secrets, etc.) managed and injected by Doppler at runtime.

## Changes Made

### New Files
- `docs/decisions/012-doppler-secrets-management.md` - ADR documenting Doppler integration decisions

### Modified Files
- `replit.md`:
  - Added Doppler to Tech Stack
  - Added ADR-012 reference
  - Added this change log entry

### Configuration Changes
- Installed `doppler` system package via Nix
- Added `DOPPLER_TOKEN` as Replit secret
- Updated Backend workflow: `doppler run --project docsense --config dev --preserve-env -- uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
- Updated Frontend workflow: `doppler run --project docsense --config dev --preserve-env -- bash -c "cd client && npm run dev"`

## Rationale

Centralizing secrets in Doppler provides:
- Single source of truth for all secrets across environments
- Audit logging for secret access
- Easier secret rotation
- Team-based access controls
- Consistent developer experience across local and cloud environments

The `--preserve-env` flag ensures Replit-managed variables (like `DATABASE_URL`) take precedence, preventing conflicts with Doppler values.

## Technical Details

### Doppler Configuration
- **Project**: `docsense`
- **Config**: `dev`
- **Token Type**: Personal token (requires project/config flags)

### Secrets in Doppler
| Secret | Purpose |
|--------|---------|
| ANTHROPIC_API_KEY | Claude AI provider |
| SESSION_SECRET | User session encryption |

### Secrets in Replit
| Secret | Purpose |
|--------|---------|
| DOPPLER_TOKEN | Doppler authentication |
| DATABASE_URL | Replit PostgreSQL (managed by platform) |

## Testing
- Backend workflow starts successfully with Doppler secrets injected
- Frontend workflow starts successfully
- AI provider receives ANTHROPIC_API_KEY from Doppler

## Related ADRs
- [ADR-012: Doppler Secrets Management](../decisions/012-doppler-secrets-management.md)
- [ADR-011: AI Provider Implementation](../decisions/011-ai-provider-implementation.md)

## Next Steps
- Create staging (`stg`) and production (`prd`) configs in Doppler
- Set up CI/CD integration with Doppler for deployments
- Consider migrating DATABASE_URL to Doppler for production deployments
