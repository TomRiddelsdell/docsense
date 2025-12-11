# ADR-012: Doppler Secrets Management

## Status
Accepted

## Date
2025-12-11

## Context

The application requires management of sensitive configuration including:
- AI provider API keys (Anthropic Claude)
- Database credentials
- Session secrets
- Future third-party integrations

Initially, secrets were stored directly in Replit's built-in Secrets tool. However, as the application grows and potentially deploys to multiple environments (development, staging, production), a centralized secrets management solution provides benefits:

1. **Environment consistency**: Same secrets interface across all deployment targets
2. **Audit trail**: Track who accessed or modified secrets
3. **Secret rotation**: Easier to rotate credentials across environments
4. **Team access control**: Role-based access to secrets by environment

## Decision

We adopt **Doppler** as the centralized secrets manager with the following configuration:

### 1. Single Replit Secret

Only one secret is stored in Replit:
- `DOPPLER_TOKEN`: Service token scoped to the Doppler project

All other secrets are stored in Doppler and injected at runtime.

### 2. Doppler Project Structure

```
Project: docsense
├── dev     (development environment)
├── stg     (staging environment - future)
└── prd     (production environment - future)
```

### 3. Runtime Secret Injection

Workflows use the Doppler CLI to inject secrets:

```bash
doppler run --project docsense --config dev --preserve-env -- <command>
```

The `--preserve-env` flag ensures Replit-managed environment variables (like `DATABASE_URL` for the built-in PostgreSQL) take precedence over Doppler values.

### 4. Secrets Stored in Doppler

| Secret Name | Purpose |
|-------------|---------|
| ANTHROPIC_API_KEY | Claude AI provider authentication |
| SESSION_SECRET | User session encryption |
| (future) | Additional third-party API keys |

### 5. Secrets Managed by Replit

| Variable | Purpose |
|----------|---------|
| DATABASE_URL | PostgreSQL connection (Replit-managed) |
| REPLIT_* | Replit platform variables |

## Consequences

### Positive

- **Centralized management**: All secrets visible in one dashboard
- **Environment parity**: Same tooling across dev/staging/prod
- **Audit logging**: Track secret access and modifications
- **Easy rotation**: Update once in Doppler, all instances receive new value
- **Team collaboration**: Granular access control per environment

### Negative

- **External dependency**: Doppler availability affects application startup
- **Token management**: Must secure the `DOPPLER_TOKEN` carefully
- **Latency**: Small startup delay for secret fetching (typically <1 second)
- **Cost**: Doppler has usage-based pricing (free tier available)

### Neutral

- Developers must install Doppler CLI locally for development
- Secrets are not visible in Replit's Secrets UI (except DOPPLER_TOKEN)

## Alternatives Considered

### Continue with Replit Secrets Only

Rejected because:
- No audit trail
- Difficult to manage across multiple deployment targets
- No secret rotation support
- Limited team access controls

### HashiCorp Vault

Rejected because:
- More complex setup and maintenance
- Overkill for current application scale
- Requires self-hosting or HCP subscription

### AWS Secrets Manager

Rejected because:
- Vendor lock-in to AWS
- More complex IAM configuration
- Doppler provides simpler developer experience

## Implementation

### Workflow Commands

**Backend:**
```bash
doppler run --project docsense --config dev --preserve-env -- uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
doppler run --project docsense --config dev --preserve-env -- bash -c "cd client && npm run dev"
```

### Local Development

Developers can run locally with:
```bash
doppler run --project docsense --config dev -- python main.py
```

Or use the VS Code Doppler extension for automatic secret injection.

## References

- [Doppler Documentation](https://docs.doppler.com/)
- [Doppler CLI Reference](https://docs.doppler.com/docs/cli)
- [ADR-011: AI Provider Implementation](011-ai-provider-implementation.md)
