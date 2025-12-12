"""Configuration validation for production readiness."""
import os
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when required configuration is missing or invalid."""
    pass


def validate_required_secrets() -> List[str]:
    """
    Validate that all required secrets are configured.

    Returns:
        List of validation errors (empty if all valid)
    """
    errors = []

    # Database configuration
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        errors.append("DATABASE_URL is required")
    elif database_url == "postgresql://user:password@localhost:5432/docsense":
        errors.append("DATABASE_URL is using default/example value - set actual credentials")

    # AI Provider API Keys - at least one is required
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("AI_INTEGRATIONS_GEMINI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY")

    if not any([gemini_key, anthropic_key, openai_key]):
        errors.append("At least one AI provider API key is required (GEMINI_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY)")

    # Check for example/placeholder values
    if gemini_key and "your-gemini-api-key" in gemini_key.lower():
        errors.append("GEMINI_API_KEY contains placeholder value - set actual API key")
    if anthropic_key and "your-anthropic-api-key" in anthropic_key.lower():
        errors.append("ANTHROPIC_API_KEY contains placeholder value - set actual API key")
    if openai_key and "your-openai-api-key" in openai_key.lower():
        errors.append("OPENAI_API_KEY contains placeholder value - set actual API key")

    # Secret key for production
    environment = os.getenv("ENVIRONMENT", "development")
    secret_key = os.getenv("SECRET_KEY")

    if environment == "production":
        if not secret_key:
            errors.append("SECRET_KEY is required in production")
        elif secret_key == "your-secret-key-here":
            errors.append("SECRET_KEY is using default/example value - generate with: openssl rand -hex 32")
        elif len(secret_key) < 32:
            errors.append("SECRET_KEY should be at least 32 characters for production")

    return errors


def validate_security_config() -> List[str]:
    """
    Validate security-related configuration.

    Returns:
        List of validation warnings (empty if all valid)
    """
    warnings = []

    environment = os.getenv("ENVIRONMENT", "development")

    # CORS configuration
    cors_origins = os.getenv("CORS_ORIGINS", "")
    if cors_origins == "*" and environment == "production":
        warnings.append("CORS_ORIGINS is set to '*' in production - this is a security risk")

    # Debug mode in production
    debug = os.getenv("DEBUG", "false").lower()
    if debug == "true" and environment == "production":
        warnings.append("DEBUG is enabled in production - this may expose sensitive information")

    # API docs in production
    enable_docs = os.getenv("ENABLE_DOCS", "true").lower()
    if enable_docs == "true" and environment == "production":
        warnings.append("API documentation is enabled in production - consider disabling")

    return warnings


def validate_database_config() -> List[str]:
    """
    Validate database configuration.

    Returns:
        List of validation warnings
    """
    warnings = []

    # Check pool size configuration
    pool_min = os.getenv("DB_POOL_MIN_SIZE")
    pool_max = os.getenv("DB_POOL_MAX_SIZE")

    if pool_min and pool_max:
        try:
            min_val = int(pool_min)
            max_val = int(pool_max)

            if min_val > max_val:
                warnings.append(f"DB_POOL_MIN_SIZE ({min_val}) is greater than DB_POOL_MAX_SIZE ({max_val})")
            if min_val < 2:
                warnings.append(f"DB_POOL_MIN_SIZE ({min_val}) is very low - consider increasing for production")
            if max_val < 5:
                warnings.append(f"DB_POOL_MAX_SIZE ({max_val}) is very low - consider increasing for production")
        except ValueError:
            warnings.append("DB_POOL_MIN_SIZE or DB_POOL_MAX_SIZE is not a valid integer")

    return warnings


def validate_startup_config(fail_on_error: bool = True) -> Tuple[List[str], List[str]]:
    """
    Validate all configuration at startup.

    Args:
        fail_on_error: If True, raise exception on validation errors

    Returns:
        Tuple of (errors, warnings)

    Raises:
        ConfigValidationError: If fail_on_error is True and there are validation errors
    """
    errors = []
    warnings = []

    # Collect all validation results
    errors.extend(validate_required_secrets())
    warnings.extend(validate_security_config())
    warnings.extend(validate_database_config())

    # Log results
    if errors:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")

    if warnings:
        logger.warning("Configuration validation warnings:")
        for warning in warnings:
            logger.warning(f"  - {warning}")

    # Fail if requested
    if fail_on_error and errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ConfigValidationError(error_msg)

    return errors, warnings
