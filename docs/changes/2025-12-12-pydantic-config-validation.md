# Configuration Validation with Pydantic Settings

**Date**: 2025-12-12
**Author**: Claude Code
**Type**: Enhancement
**Status**: Completed

## Summary

Implemented comprehensive secret and configuration validation at application startup using Pydantic BaseSettings. The application now fails fast with clear, actionable error messages if required configuration is missing or invalid, preventing cryptic runtime failures.

## Motivation

Previously, the application used ad-hoc environment variable reading with minimal validation. This led to:
- Runtime failures with unclear error messages
- Missing configuration discovered late in execution
- Placeholder values accidentally deployed to production
- Difficult debugging of configuration issues

The new Pydantic-based approach provides:
- **Type-safe configuration** with automatic validation
- **Fail-fast behavior** at startup with clear error messages
- **Production security checks** preventing common misconfigurations
- **Better IDE support** with autocomplete and type checking

## Changes

### New Files

#### `/src/api/config.py`
- Comprehensive Pydantic `Settings` class with all environment variables
- Field validators for required fields, placeholder detection, and production security
- Model validators for cross-field validation (e.g., at least one AI provider)
- Helper methods: `get_available_ai_providers()`, `get_cors_origins_list()`, `log_startup_info()`
- Singleton pattern with `get_settings()` and `reset_settings()` for testing

**Key Validations**:
- `DATABASE_URL`: Required, must be PostgreSQL, no placeholders
- AI Provider Keys: At least one required (Gemini, Claude, or OpenAI)
- `CORS_ORIGINS`: Required, no wildcards in production
- `SECRET_KEY`: Required in production, min 32 chars, no placeholders
- Pool sizes: Min cannot exceed max
- Log level: Must be valid (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- AI provider: Must be valid (gemini, claude, openai)

#### `/tests/unit/api/test_config.py`
- 24 comprehensive tests covering all validation scenarios
- Tests for required fields, placeholder detection, production security
- Tests for helper methods and default values
- Tests for cross-field validation

#### `/docs/deployment/environment-variables.md`
- Comprehensive reference documentation for all environment variables
- Security best practices and production checklists
- Common error messages and troubleshooting guide
- Configuration examples for development and production

### Modified Files

#### `/src/api/main.py`
- Updated `lifespan()` to use Pydantic Settings with better error formatting
- Updated `create_app()` to use Settings for CORS configuration
- Added conditional app creation to support testing (only create app if not running pytest)
- Removed manual environment variable parsing in favor of Settings object

#### `/src/api/dependencies.py`
- Removed local `Settings` dataclass (replaced by Pydantic version)
- Removed `get_settings()` function (now imported from config.py)
- Updated `Container._initialize()` to use uppercase attribute names (`DATABASE_URL`, `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`)
- Added import of Settings from config module

#### `/src/api/routes/projection_admin.py`
- Fixed incorrect import: `src.infrastructure.event_store.store` → `src.infrastructure.persistence.event_store`
- Updated to import `PostgresEventStore` instead of non-existent `EventStore`

#### `pyproject.toml`
- Added `pydantic-settings = "^2.12.0"` dependency

#### `/docs/deployment/` (directory created)
- New deployment documentation directory for operational guides

## Technical Details

### Pydantic Settings Features Used

1. **BaseSettings**: Automatic environment variable loading
2. **Field validators**: Single-field validation with `@field_validator`
3. **Model validators**: Cross-field validation with `@model_validator`
4. **Field metadata**: Descriptions, defaults, and constraints
5. **Type hints**: Automatic type conversion and validation

### Validation Strategy

- **Required fields**: Fail immediately if missing
- **Placeholder detection**: Reject common placeholder patterns
- **Production security**: Stricter validation in production environment
- **Development flexibility**: Warnings instead of errors for some issues in development
- **Clear error messages**: Specific, actionable error messages

### Testing Strategy

- **Fixture-based**: Use pytest fixtures to set up environment variables
- **Isolated tests**: `reset_settings()` before each test for isolation
- **Comprehensive coverage**: Test valid cases, invalid cases, edge cases
- **Production scenarios**: Specific tests for production validation

## Breaking Changes

### For Developers

- `DATABASE_URL` now strictly validated (must be PostgreSQL, no placeholders)
- At least one AI provider API key now required (will fail if none set)
- `CORS_ORIGINS` cannot be empty or wildcard in production
- Application will fail to start if configuration is invalid

### Migration Guide

1. **Update `.env` file**:
   - Ensure `DATABASE_URL` is a valid PostgreSQL connection string
   - Set at least one AI provider key (not placeholder)
   - Set `CORS_ORIGINS` to actual frontend URLs (not `*` in production)

2. **Production deployment**:
   - Set `SECRET_KEY` (generate with `openssl rand -hex 32`)
   - Set `ENVIRONMENT=production`
   - Review and test all environment variables

3. **Testing**:
   - Tests can use fixtures to set environment variables
   - Use `reset_settings()` to clear singleton between tests

## Rationale

This change implements "fail fast" principles:
- Configuration errors discovered at startup, not runtime
- Clear error messages make debugging trivial
- Production security enforced automatically
- Developer experience improved with type safety

### Alternatives Considered

1. **Keep existing validation**: Too error-prone, unclear messages
2. **Use python-decouple**: Less type safety than Pydantic
3. **Custom validation class**: Pydantic is battle-tested and feature-rich

## Related

- See [Environment Variables Reference](/docs/deployment/environment-variables.md) for complete documentation
- See [ADR-012: Doppler Secret Management](/docs/decisions/012-doppler-secret-management.md) for secret management

## Next Steps

None required - implementation is complete and tested.

## Testing

All 24 configuration tests pass:
- Valid configuration scenarios
- Missing required fields
- Placeholder value detection
- Production security validation
- Helper method functionality
- Default value validation

Run tests with:
```bash
PYTHONPATH=/workspaces poetry run pytest tests/unit/api/test_config.py -v
```

## Rollback Plan

If issues arise:
1. Revert changes to `main.py`, `dependencies.py`, `config.py`
2. Remove `pydantic-settings` from dependencies
3. Restore original validation from `src/infrastructure/config/validation.py`

## Security Considerations

This change **improves** security by:
- Preventing wildcard CORS in production
- Enforcing strong SECRET_KEY requirements
- Detecting placeholder values before deployment
- Validating all security-critical configuration

## Performance Impact

Minimal:
- Configuration validated once at startup
- Singleton pattern prevents re-validation
- No runtime performance impact
