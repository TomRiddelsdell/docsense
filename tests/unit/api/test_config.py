"""
Tests for configuration validation module.
"""
import os
import pytest
from pydantic import ValidationError
from src.api.config import Settings, get_settings, reset_settings


@pytest.fixture(autouse=True)
def reset_config():
    """Reset settings singleton before each test."""
    reset_settings()
    yield
    reset_settings()


@pytest.fixture
def valid_env_vars(monkeypatch):
    """Set up valid environment variables for testing."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key-123")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key-456")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key-789")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5000")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-" + "x" * 32)
    monkeypatch.setenv("ENVIRONMENT", "development")


class TestSettingsValidation:
    """Test configuration validation."""

    def test_valid_configuration(self, valid_env_vars):
        """Test that valid configuration passes validation."""
        settings = Settings()

        assert settings.DATABASE_URL == "postgresql://testuser:testpass@localhost:5432/testdb"
        assert settings.GEMINI_API_KEY == "test-gemini-key-123"
        assert settings.ANTHROPIC_API_KEY == "test-anthropic-key-456"
        assert settings.OPENAI_API_KEY == "test-openai-key-789"
        assert settings.CORS_ORIGINS == "http://localhost:5000"
        assert settings.ENVIRONMENT == "development"

    def test_database_url_required(self, monkeypatch):
        """Test that DATABASE_URL is required."""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5000")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        assert any(e['loc'] == ('DATABASE_URL',) for e in errors)

    def test_database_url_placeholder_rejected(self, monkeypatch):
        """Test that placeholder DATABASE_URL is rejected."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://user:password@localhost:5432/docsense")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("placeholder" in msg.lower() for msg in error_msgs)

    def test_database_url_must_be_postgresql(self, monkeypatch):
        """Test that DATABASE_URL must be a PostgreSQL connection string."""
        monkeypatch.setenv("DATABASE_URL", "mysql://testuser:testpass@localhost:3306/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("postgresql" in msg.lower() for msg in error_msgs)

    def test_at_least_one_ai_provider_required(self, monkeypatch):
        """Test that at least one AI provider API key is required."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5000")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = str(errors)
        assert "ai provider api key" in error_msgs.lower()

    def test_placeholder_api_keys_rejected(self, monkeypatch):
        """Test that placeholder API keys are rejected."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "your-gemini-api-key-here")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("placeholder" in msg.lower() for msg in error_msgs)

    def test_cors_origins_required(self, monkeypatch):
        """Test that CORS_ORIGINS is validated."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("CORS_ORIGINS", "")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("cors" in msg.lower() for msg in error_msgs)

    def test_wildcard_cors_rejected_in_production(self, monkeypatch):
        """Test that wildcard CORS is rejected in production."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("SECRET_KEY", "x" * 32)

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("wildcard" in msg.lower() or "*" in msg for msg in error_msgs)

    def test_wildcard_cors_allowed_in_development(self, monkeypatch, caplog):
        """Test that wildcard CORS is allowed in development with warning."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        monkeypatch.setenv("ENVIRONMENT", "development")

        settings = Settings()
        assert settings.CORS_ORIGINS == "*"

    def test_production_secret_key_required(self, monkeypatch):
        """Test that SECRET_KEY is required in production."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("CORS_ORIGINS", "https://example.com")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("secret_key" in msg.lower() for msg in error_msgs)

    def test_production_secret_key_placeholder_rejected(self, monkeypatch):
        """Test that placeholder SECRET_KEY is rejected in production."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
        monkeypatch.setenv("SECRET_KEY", "your-secret-key-here")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("placeholder" in msg.lower() for msg in error_msgs)

    def test_production_secret_key_too_short(self, monkeypatch):
        """Test that short SECRET_KEY is rejected in production."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
        monkeypatch.setenv("SECRET_KEY", "short")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("32 characters" in msg.lower() for msg in error_msgs)

    def test_pool_size_validation(self, monkeypatch):
        """Test that pool min size cannot exceed max size."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("DB_POOL_MIN_SIZE", "20")
        monkeypatch.setenv("DB_POOL_MAX_SIZE", "10")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("pool" in msg.lower() for msg in error_msgs)

    def test_invalid_log_level(self, monkeypatch):
        """Test that invalid log level is rejected."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("LOG_LEVEL", "INVALID")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("log_level" in msg.lower() for msg in error_msgs)

    def test_valid_log_levels(self, valid_env_vars, monkeypatch):
        """Test that valid log levels are accepted."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

        for level in valid_levels:
            reset_settings()
            monkeypatch.setenv("LOG_LEVEL", level)
            settings = Settings()
            assert settings.LOG_LEVEL == level

    def test_invalid_ai_provider(self, monkeypatch):
        """Test that invalid AI provider is rejected."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("DEFAULT_AI_PROVIDER", "invalid")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        errors = exc_info.value.errors()
        error_msgs = [e['msg'] for e in errors]
        assert any("default_ai_provider" in msg.lower() for msg in error_msgs)

    def test_alternative_api_key_naming(self, monkeypatch):
        """Test that alternative API key naming conventions work."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("AI_INTEGRATIONS_GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5000")

        settings = Settings()
        assert settings.AI_INTEGRATIONS_GEMINI_API_KEY == "test-key"


class TestSettingsHelperMethods:
    """Test helper methods on Settings."""

    def test_get_available_ai_providers(self, valid_env_vars):
        """Test getting list of available AI providers."""
        settings = Settings()
        providers = settings.get_available_ai_providers()

        assert 'gemini' in providers
        assert 'claude' in providers
        assert 'openai' in providers

    def test_get_available_ai_providers_partial(self, monkeypatch):
        """Test getting available providers when only some are configured."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5000")

        settings = Settings()
        providers = settings.get_available_ai_providers()

        assert 'claude' in providers
        assert 'gemini' not in providers
        assert 'openai' not in providers

    def test_get_cors_origins_list(self, monkeypatch):
        """Test parsing CORS_ORIGINS into a list."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5000,https://example.com,https://app.example.com")

        settings = Settings()
        origins = settings.get_cors_origins_list()

        assert len(origins) == 3
        assert "http://localhost:5000" in origins
        assert "https://example.com" in origins
        assert "https://app.example.com" in origins

    def test_get_cors_origins_list_with_spaces(self, monkeypatch):
        """Test that CORS origins are trimmed properly."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5000 , https://example.com ,  https://app.example.com")

        settings = Settings()
        origins = settings.get_cors_origins_list()

        assert len(origins) == 3
        assert all(origin == origin.strip() for origin in origins)


class TestGetSettings:
    """Test get_settings singleton."""

    def test_get_settings_singleton(self, valid_env_vars):
        """Test that get_settings returns a singleton."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_get_settings_validation_error(self, monkeypatch):
        """Test that get_settings raises on validation error."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        # Missing AI provider key

        with pytest.raises(ValidationError):
            get_settings()


class TestDefaultValues:
    """Test default configuration values."""

    def test_default_values(self, monkeypatch):
        """Test that default values are set correctly."""
        monkeypatch.setenv("DATABASE_URL", "postgresql://testuser:testpass@localhost:5432/testdb")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        # Don't set optional values

        settings = Settings()

        assert settings.ENVIRONMENT == "development"
        assert settings.PORT == 8000
        assert settings.API_BASE_PATH == "/api/v1"
        assert settings.DEBUG is False
        assert settings.DB_POOL_MIN_SIZE == 5
        assert settings.DB_POOL_MAX_SIZE == 20
        assert settings.DEFAULT_AI_PROVIDER == "gemini"
        assert settings.AI_REQUEST_TIMEOUT == 120
        assert settings.AI_MAX_RETRIES == 3
        assert settings.LOG_LEVEL == "INFO"
        assert settings.LOG_FORMAT == "json"
        assert settings.SAVE_AI_RESPONSES is False
        assert settings.ANALYTICS_ENABLED is False
        assert settings.HOT_RELOAD is False
        assert settings.ENABLE_DOCS is True
