# Environment Variables Reference

This document provides a comprehensive reference for all environment variables used in the Trading Algorithm Document Analyzer application.

## Critical Requirements

The application validates all configuration at startup using Pydantic. If required variables are missing or invalid, the application will **fail immediately** with a clear error message indicating what needs to be fixed.

### Fail-Fast Behavior

The application implements "fail fast" startup validation:
- In **production**: Application will refuse to start if required configuration is missing or invalid
- In **development**: Application may start with warnings, but critical errors will still cause startup failure
- All errors are logged with clear, actionable messages

## Required Environment Variables

### Database Configuration

#### `DATABASE_URL` (Required)

PostgreSQL connection string for the event store and read models.

- **Format**: `postgresql://user:password@host:port/database`
- **Example**: `postgresql://docsense:secure_password@db.example.com:5432/docsense`
- **Validation**:
  - Must start with `postgresql://` or `postgres://`
  - Cannot be a placeholder value (e.g., `user:password@localhost`)
  - Must be a valid PostgreSQL connection string

**Production Checklist**:
- [ ] Real database credentials (not placeholder values)
- [ ] Secure password (generated, not default)
- [ ] Database server is accessible from application
- [ ] Database exists and schema is initialized
- [ ] User has appropriate permissions

### AI Provider API Keys

**At least one AI provider API key must be configured.** The application supports multiple AI providers and will validate that at least one is available.

#### `GEMINI_API_KEY` (Optional, but one AI key required)

Google Gemini API key for AI-powered document analysis.

- **Where to get**: [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Example**: `AIzaSy...` (starts with `AIza`)
- **Validation**: Cannot contain placeholder text like "your-gemini-api-key"

#### `ANTHROPIC_API_KEY` (Optional, but one AI key required)

Anthropic Claude API key for AI-powered document analysis.

- **Where to get**: [Anthropic Console](https://console.anthropic.com/)
- **Example**: `sk-ant-...`
- **Validation**: Cannot contain placeholder text like "your-anthropic-api-key"

#### `OPENAI_API_KEY` (Optional, but one AI key required)

OpenAI GPT API key for AI-powered document analysis.

- **Where to get**: [OpenAI Platform](https://platform.openai.com/api-keys)
- **Example**: `sk-...`
- **Validation**: Cannot contain placeholder text like "your-openai-api-key"

#### Alternative Naming Convention

Some modules also recognize these alternative names:
- `AI_INTEGRATIONS_GEMINI_API_KEY` (alternative to `GEMINI_API_KEY`)
- `AI_INTEGRATIONS_OPENAI_API_KEY` (alternative to `OPENAI_API_KEY`)

**Note**: At least one of these API keys must be set. The application will fail to start if no AI provider is configured.

### CORS Configuration

#### `CORS_ORIGINS` (Required)

Comma-separated list of allowed origins for Cross-Origin Resource Sharing (CORS).

- **Format**: Comma-separated list of URLs (no spaces recommended)
- **Development Example**: `http://localhost:5000,http://localhost:3000`
- **Production Example**: `https://app.example.com,https://www.example.com`
- **Validation**:
  - Cannot be empty
  - Cannot be `*` (wildcard) in production
  - Must be specific origins including protocol and port

**Security Notes**:
- NEVER use `*` in production - this is a critical security vulnerability
- Wildcard `*` cannot be used with `allow_credentials=True` (CORS policy)
- Always specify exact origins including protocol (`http://` or `https://`)
- Do not include trailing slashes
- In production, must be your actual frontend domain(s)

**Production Checklist**:
- [ ] Real domain names (not `localhost`)
- [ ] HTTPS protocol (not HTTP)
- [ ] No wildcard (`*`)
- [ ] All expected frontend origins included

### Production Security

#### `SECRET_KEY` (Required in production, optional in development)

Secret key used for JWT/session signing and other cryptographic operations.

- **How to generate**: `openssl rand -hex 32`
- **Example**: `a1b2c3d4e5f6...` (64 hex characters)
- **Validation (production only)**:
  - Must be set (cannot be empty)
  - Cannot be placeholder value (`your-secret-key-here`)
  - Must be at least 32 characters long

**Production Checklist**:
- [ ] Generated using cryptographically secure method
- [ ] At least 32 characters long
- [ ] Stored securely (not in version control)
- [ ] Unique to this environment

#### `ENVIRONMENT` (Default: `development`)

Environment name used to determine validation strictness.

- **Valid values**: `development`, `staging`, `production`
- **Default**: `development`
- **Effect**:
  - `production`: Strict validation, all security checks enforced
  - `development`: Relaxed validation, warnings instead of errors

## Optional Configuration

### Database Pool Settings

#### `DB_POOL_MIN_SIZE` (Default: `5`)

Minimum number of database connections in the pool.

- **Type**: Integer
- **Range**: 1-50
- **Recommended**: 2-10 for production

#### `DB_POOL_MAX_SIZE` (Default: `20`)

Maximum number of database connections in the pool.

- **Type**: Integer
- **Range**: 1-100
- **Recommended**: 10-50 for production
- **Validation**: Must be greater than or equal to `DB_POOL_MIN_SIZE`

### Application Settings

#### `PORT` (Default: `8000`)

Port number for the application server.

- **Type**: Integer
- **Range**: 1-65535

#### `API_BASE_PATH` (Default: `/api/v1`)

Base path prefix for all API routes.

#### `DEBUG` (Default: `false`)

Enable debug mode for development.

- **Type**: Boolean (`true` or `false`)
- **Security**: Should be `false` in production
- **Warning**: If `true` in production, a warning is logged

### AI Analysis Settings

#### `DEFAULT_AI_PROVIDER` (Default: `gemini`)

Default AI provider to use for analysis.

- **Valid values**: `gemini`, `claude`, `openai`
- **Requirement**: The selected provider's API key must be configured

#### `AI_REQUEST_TIMEOUT` (Default: `120`)

Timeout for AI API requests in seconds.

- **Type**: Integer
- **Minimum**: 1

#### `AI_MAX_RETRIES` (Default: `3`)

Maximum number of retries for failed AI API requests.

- **Type**: Integer
- **Minimum**: 0

### Logging Configuration

#### `LOG_LEVEL` (Default: `INFO`)

Logging verbosity level.

- **Valid values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Case insensitive**: Automatically converted to uppercase
- **Production Recommendation**: `INFO` or `WARNING`

#### `LOG_FORMAT` (Default: `json`)

Log output format.

- **Valid values**: `json`, `text`
- **Recommendation**: `json` for production (easier to parse and analyze)

#### `SAVE_AI_RESPONSES` (Default: `false`)

Enable saving AI responses to files for debugging.

- **Type**: Boolean
- **Use case**: Development debugging only

### Storage Configuration

#### `UPLOAD_DIR` (Default: `./uploads`)

Directory path for storing uploaded documents.

#### `MAX_UPLOAD_SIZE` (Default: `10485760`)

Maximum file upload size in bytes.

- **Default**: 10MB (`10485760` bytes)
- **Type**: Integer
- **Minimum**: 1

### External Services

#### `SENTRY_DSN` (Default: none)

Sentry Data Source Name for error tracking.

- **Optional**: Only needed if using Sentry

#### `ANALYTICS_ENABLED` (Default: `false`)

Enable analytics and monitoring.

- **Type**: Boolean

### Development Tools

#### `HOT_RELOAD` (Default: `false`)

Enable hot reload in development mode.

- **Type**: Boolean
- **Use case**: Development only

#### `ENABLE_DOCS` (Default: `true`)

Enable API documentation endpoints (Swagger/ReDoc).

- **Type**: Boolean
- **Security**: Consider disabling in production (`false`)
- **Warning**: If `true` in production, a warning is logged

## Configuration File Examples

### Minimum Required Configuration

```bash
# Database (required)
DATABASE_URL=postgresql://user:password@localhost:5432/docsense

# At least one AI provider (required)
GEMINI_API_KEY=your-actual-api-key-here

# CORS (required)
CORS_ORIGINS=http://localhost:5000
```

### Production Configuration

```bash
# Environment
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://docsense_prod:SECURE_PASSWORD@db.prod.example.com:5432/docsense_prod
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20

# AI Providers (all configured for redundancy)
GEMINI_API_KEY=AIzaSy...
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
DEFAULT_AI_PROVIDER=gemini

# Security
SECRET_KEY=<output-of-openssl-rand-hex-32>
CORS_ORIGINS=https://app.example.com,https://www.example.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Features
DEBUG=false
ENABLE_DOCS=false

# External Services
SENTRY_DSN=https://...@sentry.io/...
```

### Development Configuration

```bash
# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=postgresql://docsense:docsense_local_dev@localhost:5432/docsense

# AI Provider (just one for development)
GEMINI_API_KEY=AIzaSy...

# CORS
CORS_ORIGINS=http://localhost:5000,http://localhost:3000

# Development Features
DEBUG=true
HOT_RELOAD=true
ENABLE_DOCS=true
LOG_LEVEL=DEBUG
SAVE_AI_RESPONSES=true
```

## Using Doppler for Secret Management

Instead of managing `.env` files manually, you can use [Doppler](https://www.doppler.com/) for centralized secret management.

See [ADR-012: Doppler Secret Management](../decisions/012-doppler-secret-management.md) for details.

```bash
# Install Doppler CLI
brew install doppler  # macOS
# or: curl -sLf --tlsv1.2 --proto =https https://cli.doppler.com/install.sh | sh

# Login and setup
doppler login
doppler setup

# Run with Doppler
doppler run -- python main.py
```

## Validation Error Messages

When the application starts, it validates all configuration using Pydantic. Here are examples of error messages you might see:

### Missing Required Field

```
Configuration validation failed:
  DATABASE_URL: Field required
```

**Fix**: Set the `DATABASE_URL` environment variable.

### Placeholder Value

```
Configuration validation failed:
  DATABASE_URL: DATABASE_URL appears to be a placeholder. Set actual database credentials.
```

**Fix**: Replace the placeholder value with actual credentials.

### No AI Provider

```
Configuration validation failed:
  : At least one AI provider API key must be configured. Set one of: GEMINI_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY
```

**Fix**: Set at least one AI provider API key.

### Production Security Error

```
Configuration validation failed:
  CORS_ORIGINS: CORS_ORIGINS cannot be '*' (wildcard) in production. Specify exact origins for security.
```

**Fix**: Set `CORS_ORIGINS` to specific domain(s) instead of `*`.

## Troubleshooting

### Application Won't Start

1. Check the error message - it will tell you exactly which configuration is missing or invalid
2. Ensure all required variables are set
3. Verify no placeholder values remain
4. Check that at least one AI provider API key is configured
5. For production, ensure `SECRET_KEY` is set and valid

### CORS Errors in Browser

1. Check that `CORS_ORIGINS` includes your frontend URL
2. Ensure the protocol (http/https) matches exactly
3. Ensure the port number (if any) is included
4. Verify no trailing slashes in URLs

### Database Connection Failures

1. Verify `DATABASE_URL` format is correct
2. Test database connectivity: `psql $DATABASE_URL`
3. Check database exists and user has permissions
4. Ensure database server is accessible from application server

## References

- [Configuration Module](/src/api/config.py) - Pydantic configuration implementation
- [Environment Variables Template](/.env.example) - Template with all variables
- [ADR-012: Doppler Secret Management](/docs/decisions/012-doppler-secret-management.md)
