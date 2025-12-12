# ADR-012: Doppler Secret Management

## Status

Accepted

## Date

2025-12-08

## Context

The Trading Algorithm Document Analyzer requires secure management of sensitive credentials including:
- AI provider API keys (Google Gemini, Anthropic Claude, OpenAI)
- Database connection strings
- Third-party service credentials
- Environment-specific configuration

Hardcoding secrets in code or storing them in version control poses significant security risks. The application needs a centralized, secure secret management solution that:
1. Prevents secrets from being committed to version control
2. Allows environment-specific secret management (dev, staging, production)
3. Supports team collaboration with access controls
4. Enables easy secret rotation without code changes
5. Works seamlessly with local development and deployment environments

## Decision

We will use **Doppler** as our centralized secret management solution with the following implementation:

### 1. Secret Storage in Doppler

All secrets will be stored in Doppler and organized by environment:
- **Development** (dev) - For local development
- **Staging** (stg) - For testing and QA
- **Production** (prd) - For live deployment

### 2. Secret Access Pattern

**Backend (Python/FastAPI):**
- Use the `python-dotenv` library to load environment variables
- Doppler CLI injects secrets as environment variables at runtime
- Access secrets via `os.getenv()` or Pydantic `Settings` classes
- Never reference Doppler API directly in application code

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # AI Provider Keys
    gemini_api_key: str
    anthropic_api_key: str
    openai_api_key: str

    # Database
    database_url: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

**Frontend (React/TypeScript):**
- Frontend should NOT have direct access to secrets
- All API keys and sensitive data must remain server-side
- Environment variables prefixed with `VITE_` for non-sensitive config only
- Backend proxies all third-party API calls

### 3. Local Development Workflow

```bash
# Install Doppler CLI
curl -Ls https://cli.doppler.com/install.sh | sh

# Authenticate
doppler login

# Setup project
doppler setup

# Run application with Doppler
doppler run -- python main.py
doppler run -- poetry run uvicorn src.api.main:app

# Or use doppler to generate .env file (not recommended for production)
doppler secrets download --no-file --format env > .env
```

### 4. Deployment Workflow

**Container/Docker Deployment:**
```dockerfile
# Install Doppler in container
RUN apt-get update && apt-get install -y apt-transport-https ca-certificates curl gnupg && \
    curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | apt-key add - && \
    echo "deb https://packages.doppler.com/public/cli/deb/debian any-version main" | tee /etc/apt/sources.list.d/doppler-cli.list && \
    apt-get update && apt-get install -y doppler

# Use Doppler to inject secrets at runtime
CMD ["doppler", "run", "--", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Cloud Platform Deployment:**
- Use Doppler integrations for AWS, GCP, Azure, Heroku, Vercel, etc.
- Doppler automatically syncs secrets to platform secret managers
- Platform injects secrets as environment variables

### 5. Secret Naming Conventions

Use UPPER_SNAKE_CASE for all secret names:
- AI Keys: `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`
- Database: `DATABASE_URL`, `DB_HOST`, `DB_PASSWORD`
- External Services: `AWS_ACCESS_KEY_ID`, `STRIPE_SECRET_KEY`

### 6. Security Best Practices

1. **Never commit secrets** - Add `.env`, `.env.*`, and `doppler.yaml` to `.gitignore`
2. **Use service tokens** - For CI/CD, use Doppler service tokens, not personal tokens
3. **Principle of least privilege** - Grant minimum required access per environment
4. **Rotate regularly** - Establish a secret rotation schedule
5. **Audit access** - Review Doppler audit logs regularly

### 7. Fallback for Local Development (Optional)

For developers who cannot use Doppler:
1. Create `.env.example` with dummy values
2. Copy to `.env` and fill in real values
3. **NEVER** commit `.env` to version control
4. Document all required environment variables in `.env.example`

## Consequences

### Positive

- **Enhanced Security**: Secrets never stored in code or version control
- **Centralized Management**: Single source of truth for all secrets across environments
- **Easy Rotation**: Update secrets in Doppler without code changes
- **Team Collaboration**: Controlled access with audit trails
- **Environment Parity**: Consistent secret management across dev, staging, production
- **Reduced Onboarding Friction**: New developers can quickly access required secrets
- **Audit Trail**: Complete history of secret access and changes
- **Integration Support**: Native integrations with major cloud platforms and CI/CD tools

### Negative

- **Additional Dependency**: Requires Doppler CLI for local development
- **Vendor Lock-in**: Migration to another secret manager requires workflow changes
- **Internet Dependency**: Doppler CLI requires internet connection to fetch secrets
- **Learning Curve**: Team needs to learn Doppler CLI and workflows
- **Cost**: Doppler has usage limits on free tier; paid plans required for larger teams

### Neutral

- **Deployment Changes**: CI/CD pipelines must be updated to use Doppler
- **Documentation Overhead**: Must maintain documentation for secret setup
- **Backup Strategy**: Need process for backing up secrets outside Doppler

## Alternatives Considered

### 1. Environment Variables Only (.env files)

**Pros:**
- Simple and well-understood
- No external dependencies
- Works offline

**Cons:**
- No centralized management
- Secrets easily committed by mistake
- No audit trail
- Difficult to share across team
- Manual rotation process

**Why Not Chosen:** Doesn't scale for team collaboration and lacks security features

### 2. AWS Secrets Manager / GCP Secret Manager

**Pros:**
- Native cloud integration
- No additional vendor
- Robust security features

**Cons:**
- Cloud-specific (not portable)
- More complex local development setup
- Requires cloud account for development
- Higher learning curve

**Why Not Chosen:** Adds cloud dependency for local development; Doppler provides cloud integrations anyway

### 3. HashiCorp Vault

**Pros:**
- Enterprise-grade secret management
- Self-hosted option
- Dynamic secret generation
- Extensive authentication methods

**Cons:**
- Complex setup and maintenance
- Requires infrastructure to run Vault server
- Overkill for project size
- Steep learning curve

**Why Not Chosen:** Too complex for current project needs; Doppler offers better developer experience

### 4. Git-crypt / SOPS (Secrets in Git)

**Pros:**
- Secrets stored with code
- Version controlled
- No external service

**Cons:**
- Still stores encrypted secrets in git
- Complex key management
- Difficult audit trail
- No web UI for management
- Team members need encryption keys

**Why Not Chosen:** Encryption adds complexity without Doppler's management benefits

## References

- [Doppler Documentation](https://docs.doppler.com/)
- [Doppler CLI Reference](https://docs.doppler.com/docs/cli)
- [Doppler Integrations](https://docs.doppler.com/docs/integrations)
- [The Twelve-Factor App: Config](https://12factor.net/config)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Pydantic Settings Management](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
