"""
Application configuration with comprehensive validation.

This module provides Pydantic-based configuration management with automatic
validation at application startup. It ensures all required secrets and settings
are properly configured before the application starts.
"""
import os
import logging
from typing import Optional, List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings with automatic validation.

    All settings are loaded from environment variables. Required settings
    will cause the application to fail at startup if not provided.

    At least one AI provider API key must be configured.
    """

    # ========================================================================
    # Database Configuration (Required)
    # ========================================================================
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection string",
    )

    DB_POOL_MIN_SIZE: int = Field(
        default=5,
        ge=1,
        le=1000,  # Allow high values but warn via validator
        description="Minimum database connection pool size"
    )

    DB_POOL_MAX_SIZE: int = Field(
        default=20,
        ge=1,
        le=1000,  # Allow high values but warn via validator
        description="Maximum database connection pool size"
    )

    # ========================================================================
    # AI Provider API Keys (At least one required)
    # ========================================================================
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="Anthropic Claude API key"
    )

    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI GPT API key"
    )

    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API key"
    )

    # Alternative naming convention (some modules use these)
    AI_INTEGRATIONS_GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API key (alternative name)"
    )

    AI_INTEGRATIONS_OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI GPT API key (alternative name)"
    )

    # ========================================================================
    # Application Settings
    # ========================================================================
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )

    PORT: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Application server port"
    )

    API_BASE_PATH: str = Field(
        default="/api/v1",
        description="API base path prefix"
    )

    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode (development only)"
    )

    # ========================================================================
    # Security Settings
    # ========================================================================
    SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Secret key for JWT/session signing"
    )

    CORS_ORIGINS: str = Field(
        default="http://localhost:5000",
        description="Comma-separated list of allowed CORS origins"
    )

    # ========================================================================
    # Storage Configuration
    # ========================================================================
    UPLOAD_DIR: str = Field(
        default="./uploads",
        description="Document upload directory"
    )

    MAX_UPLOAD_SIZE: int = Field(
        default=10485760,  # 10MB
        ge=1,
        description="Maximum upload size in bytes"
    )

    # ========================================================================
    # AI Analysis Settings
    # ========================================================================
    DEFAULT_AI_PROVIDER: str = Field(
        default="gemini",
        description="Default AI provider: gemini, claude, openai"
    )

    AI_REQUEST_TIMEOUT: int = Field(
        default=120,
        ge=1,
        description="AI request timeout in seconds"
    )

    AI_MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        description="Maximum retries for AI requests"
    )

    # ========================================================================
    # Logging Configuration
    # ========================================================================
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )

    LOG_FORMAT: str = Field(
        default="json",
        description="Log format: json, text"
    )

    SAVE_AI_RESPONSES: bool = Field(
        default=False,
        description="Enable AI response debugging (saves responses to files)"
    )

    # ========================================================================
    # External Services
    # ========================================================================
    SENTRY_DSN: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking"
    )

    ANALYTICS_ENABLED: bool = Field(
        default=False,
        description="Enable analytics/monitoring"
    )

    # ========================================================================
    # Development Tools
    # ========================================================================
    HOT_RELOAD: bool = Field(
        default=False,
        description="Enable hot reload in development"
    )

    ENABLE_DOCS: bool = Field(
        default=True,
        description="Enable API documentation"
    )

    # ========================================================================
    # Local Development Authentication Bypass (ADR-023)
    # ========================================================================
    DEV_AUTH_BYPASS: bool = Field(
        default=False,
        description="Enable auth bypass for local development (NEVER use in production)"
    )

    DEV_TEST_USER_KERBEROS: str = Field(
        default="devusr",
        description="Test user Kerberos ID for development mode (must be 6 characters)"
    )

    DEV_TEST_USER_NAME: str = Field(
        default="Test User",
        description="Test user display name"
    )

    DEV_TEST_USER_EMAIL: str = Field(
        default="testuser@local.dev",
        description="Test user email"
    )

    DEV_TEST_USER_GROUPS: str = Field(
        default="testing",
        description="Comma-separated test user groups"
    )

    # ========================================================================
    # Validators
    # ========================================================================

    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate that DATABASE_URL is set and not a placeholder."""
        if not v or v.strip() == "":
            raise ValueError("DATABASE_URL must be set")

        # Check for placeholder values
        if "user:password@localhost" in v:
            raise ValueError(
                "DATABASE_URL appears to be a placeholder. "
                "Set actual database credentials."
            )

        # Basic format validation
        if not v.startswith(("postgresql://", "postgres://")):
            raise ValueError(
                "DATABASE_URL must be a PostgreSQL connection string "
                "(starting with postgresql:// or postgres://)"
            )

        return v

    @field_validator('DB_POOL_MIN_SIZE', 'DB_POOL_MAX_SIZE')
    @classmethod
    def validate_pool_size(cls, v: int, info) -> int:
        """Validate database pool sizes."""
        if info.field_name == 'DB_POOL_MIN_SIZE' and v < 2:
            logger.warning(
                f"DB_POOL_MIN_SIZE ({v}) is very low - consider increasing for production"
            )

        if info.field_name == 'DB_POOL_MAX_SIZE' and v < 5:
            logger.warning(
                f"DB_POOL_MAX_SIZE ({v}) is very low - consider increasing for production"
            )

        return v

    @field_validator('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'GEMINI_API_KEY',
                     'AI_INTEGRATIONS_GEMINI_API_KEY', 'AI_INTEGRATIONS_OPENAI_API_KEY')
    @classmethod
    def validate_api_keys(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that API keys are not placeholder values."""
        if v and "your-" in v.lower() and "-api-key" in v.lower():
            raise ValueError(
                f"{info.field_name} contains a placeholder value. "
                f"Set an actual API key or remove this variable."
            )
        return v

    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: Optional[str], info) -> Optional[str]:
        """Validate SECRET_KEY in production."""
        # Get environment from values dict (available during validation)
        environment = info.data.get('ENVIRONMENT', 'development')

        if environment == 'production':
            if not v:
                raise ValueError(
                    "SECRET_KEY is required in production. "
                    "Generate with: openssl rand -hex 32"
                )

            if v == "your-secret-key-here":
                raise ValueError(
                    "SECRET_KEY is using a placeholder value. "
                    "Generate with: openssl rand -hex 32"
                )

            if len(v) < 32:
                raise ValueError(
                    "SECRET_KEY should be at least 32 characters for production"
                )

        return v

    @field_validator('CORS_ORIGINS')
    @classmethod
    def validate_cors_origins(cls, v: str, info) -> str:
        """Validate CORS origins configuration."""
        environment = info.data.get('ENVIRONMENT', 'development')

        if not v or v.strip() == "":
            raise ValueError(
                "CORS_ORIGINS must be set to at least one origin. "
                "Example: http://localhost:5000"
            )

        # Check for wildcard in production
        if environment == 'production' and v.strip() == '*':
            raise ValueError(
                "CORS_ORIGINS cannot be '*' (wildcard) in production. "
                "Specify exact origins for security."
            )

        # Warn about wildcard in general
        if v.strip() == '*':
            logger.warning(
                "CORS_ORIGINS is set to '*' (wildcard). "
                "This is a security risk and should only be used in development."
            )

        return v

    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()

        if v_upper not in valid_levels:
            raise ValueError(
                f"LOG_LEVEL must be one of {valid_levels}, got '{v}'"
            )

        return v_upper

    @field_validator('DEFAULT_AI_PROVIDER')
    @classmethod
    def validate_ai_provider(cls, v: str) -> str:
        """Validate default AI provider."""
        valid_providers = ['gemini', 'claude', 'openai']
        v_lower = v.lower()

        if v_lower not in valid_providers:
            raise ValueError(
                f"DEFAULT_AI_PROVIDER must be one of {valid_providers}, got '{v}'"
            )

        return v_lower

    @model_validator(mode='after')
    def validate_at_least_one_ai_provider(self):
        """Validate that at least one AI provider API key is configured.
        
        In development mode with DEV_AUTH_BYPASS, AI keys are optional to allow
        testing document upload/viewing without AI analysis functionality.
        """
        # Check both naming conventions
        gemini_key = self.GEMINI_API_KEY or self.AI_INTEGRATIONS_GEMINI_API_KEY
        openai_key = self.OPENAI_API_KEY or self.AI_INTEGRATIONS_OPENAI_API_KEY
        anthropic_key = self.ANTHROPIC_API_KEY

        has_ai_key = any([gemini_key, anthropic_key, openai_key])
        
        # In dev mode with auth bypass, AI keys are optional
        if self.ENVIRONMENT == "development" and self.DEV_AUTH_BYPASS:
            if not has_ai_key:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "⚠️  No AI provider API keys configured. "
                    "AI analysis features will not be available."
                )
            return self
        
        # In other modes, require at least one AI key
        if not has_ai_key:
            raise ValueError(
                "At least one AI provider API key must be configured. "
                "Set one of: GEMINI_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY"
            )

        return self

    @model_validator(mode='after')
    def validate_pool_sizes(self):
        """Validate that pool min size is not greater than max size."""
        if self.DB_POOL_MIN_SIZE > self.DB_POOL_MAX_SIZE:
            raise ValueError(
                f"DB_POOL_MIN_SIZE ({self.DB_POOL_MIN_SIZE}) cannot be greater than "
                f"DB_POOL_MAX_SIZE ({self.DB_POOL_MAX_SIZE})"
            )

        # Warn about very high pool sizes
        if self.DB_POOL_MAX_SIZE > 500:
            logger.warning(
                f"DB_POOL_MAX_SIZE ({self.DB_POOL_MAX_SIZE}) is very high. "
                f"Each connection consumes server memory. Consider if you really need >500 connections. "
                f"Typical production values are 20-100."
            )

        if self.DB_POOL_MIN_SIZE > 100:
            logger.warning(
                f"DB_POOL_MIN_SIZE ({self.DB_POOL_MIN_SIZE}) is very high. "
                f"This will keep many idle connections open. "
                f"Typical production values are 5-20."
            )

        return self

    @model_validator(mode='after')
    def validate_dev_auth_bypass(self):
        """Ensure DEV_AUTH_BYPASS is NEVER enabled in production and validate test user."""
        if self.DEV_AUTH_BYPASS and self.ENVIRONMENT == "production":
            raise ValueError(
                "🚨 CRITICAL SECURITY ERROR: DEV_AUTH_BYPASS cannot be enabled "
                "in production environment! This would bypass all authentication."
            )

        if self.DEV_AUTH_BYPASS:
            # Validate test user Kerberos ID is exactly 6 characters
            if len(self.DEV_TEST_USER_KERBEROS) != 6:
                raise ValueError(
                    f"DEV_TEST_USER_KERBEROS must be exactly 6 characters (Kerberos ID format), "
                    f"got {len(self.DEV_TEST_USER_KERBEROS)}: '{self.DEV_TEST_USER_KERBEROS}'"
                )
            
            logger.warning(
                "⚠️  DEV_AUTH_BYPASS is enabled. Authentication is bypassed for local development."
            )

        return self

    @model_validator(mode='after')
    def validate_production_security(self):
        """Additional security validations for production environment."""
        if self.ENVIRONMENT != 'production':
            return self

        # Debug mode should be off in production
        if self.DEBUG:
            logger.warning(
                "DEBUG is enabled in production - this may expose sensitive information. "
                "Consider setting DEBUG=false"
            )

        # API docs should be disabled in production
        if self.ENABLE_DOCS:
            logger.warning(
                "API documentation is enabled in production. "
                "Consider setting ENABLE_DOCS=false for security."
            )

        return self

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def get_available_ai_providers(self) -> List[str]:
        """Get list of configured AI providers."""
        providers = []

        if self.GEMINI_API_KEY or self.AI_INTEGRATIONS_GEMINI_API_KEY:
            providers.append('gemini')

        if self.ANTHROPIC_API_KEY:
            providers.append('claude')

        if self.OPENAI_API_KEY or self.AI_INTEGRATIONS_OPENAI_API_KEY:
            providers.append('openai')

        return providers

    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    def log_startup_info(self) -> None:
        """Log configuration information at startup."""
        logger.info("=" * 70)
        logger.info("Configuration validated successfully")
        logger.info("=" * 70)
        logger.info(f"Environment: {self.ENVIRONMENT}")
        logger.info(f"Database: {self.DATABASE_URL[:30]}...")
        logger.info(f"Database Pool: min={self.DB_POOL_MIN_SIZE}, max={self.DB_POOL_MAX_SIZE}")
        logger.info(f"AI Providers available: {', '.join(self.get_available_ai_providers())}")
        logger.info(f"Default AI Provider: {self.DEFAULT_AI_PROVIDER}")
        logger.info(f"CORS Origins: {self.get_cors_origins_list()}")
        logger.info(f"Log Level: {self.LOG_LEVEL}")
        logger.info(f"API Port: {self.PORT}")
        logger.info(f"API Docs Enabled: {self.ENABLE_DOCS}")
        logger.info("=" * 70)

    model_config = {
        'env_file': '.env',
        'env_file_encoding': 'utf-8',
        'case_sensitive': True,
        'extra': 'ignore',  # Ignore extra environment variables
    }


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the application settings singleton.

    This function loads and validates settings on first call,
    then returns the cached instance on subsequent calls.

    Raises:
        ValidationError: If required configuration is missing or invalid

    Returns:
        Settings: Validated application settings
    """
    global _settings

    if _settings is None:
        try:
            _settings = Settings()
            _settings.log_startup_info()
        except Exception as e:
            logger.critical(f"Configuration validation failed: {e}")
            raise

    return _settings


def reset_settings() -> None:
    """Reset the settings singleton. Useful for testing."""
    global _settings
    _settings = None
