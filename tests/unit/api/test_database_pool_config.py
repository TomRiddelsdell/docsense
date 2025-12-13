"""
Tests for database connection pool configuration validation.

Tests configuration validation, warning thresholds, and health metrics.
"""
import pytest
import logging
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from src.api.config import Settings


class TestPoolSizeValidation:
    """Test database pool size validation."""

    def test_default_pool_sizes(self):
        """Test that default pool sizes are valid."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'GEMINI_API_KEY': 'test-key'
        }):
            settings = Settings()
            assert settings.DB_POOL_MIN_SIZE == 5
            assert settings.DB_POOL_MAX_SIZE == 20

    def test_custom_pool_sizes(self):
        """Test setting custom pool sizes."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'GEMINI_API_KEY': 'test-key',
            'DB_POOL_MIN_SIZE': '10',
            'DB_POOL_MAX_SIZE': '50'
        }):
            settings = Settings()
            assert settings.DB_POOL_MIN_SIZE == 10
            assert settings.DB_POOL_MAX_SIZE == 50

    def test_min_size_must_be_positive(self):
        """Test that pool min size must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MIN_SIZE': '0'
            }):
                Settings()

        assert 'DB_POOL_MIN_SIZE' in str(exc_info.value)
        assert 'greater than or equal to 1' in str(exc_info.value)

    def test_max_size_must_be_positive(self):
        """Test that pool max size must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MAX_SIZE': '0'
            }):
                Settings()

        assert 'DB_POOL_MAX_SIZE' in str(exc_info.value)


class TestPoolSizeCrossValidation:
    """Test cross-field validation between min and max pool sizes."""

    def test_min_size_equals_max_size_allowed(self):
        """Test that min size can equal max size."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'GEMINI_API_KEY': 'test-key',
            'DB_POOL_MIN_SIZE': '20',
            'DB_POOL_MAX_SIZE': '20'
        }):
            settings = Settings()
            assert settings.DB_POOL_MIN_SIZE == 20
            assert settings.DB_POOL_MAX_SIZE == 20

    def test_min_size_less_than_max_size_allowed(self):
        """Test that min size less than max size is allowed."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'GEMINI_API_KEY': 'test-key',
            'DB_POOL_MIN_SIZE': '10',
            'DB_POOL_MAX_SIZE': '30'
        }):
            settings = Settings()
            assert settings.DB_POOL_MIN_SIZE == 10
            assert settings.DB_POOL_MAX_SIZE == 30

    def test_min_size_greater_than_max_size_rejected(self):
        """Test that min size greater than max size is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MIN_SIZE': '50',
                'DB_POOL_MAX_SIZE': '20'
            }):
                Settings()

        error_msg = str(exc_info.value).lower()
        assert 'db_pool_min_size' in error_msg
        assert 'cannot be greater than' in error_msg or 'db_pool_max_size' in error_msg


class TestPoolSizeWarnings:
    """Test warning thresholds for pool sizes."""

    def test_low_min_size_triggers_warning(self, caplog):
        """Test that very low min size triggers a warning."""
        with caplog.at_level(logging.WARNING):
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MIN_SIZE': '1',
                'DB_POOL_MAX_SIZE': '20'
            }):
                Settings()

        assert any('DB_POOL_MIN_SIZE' in record.message and 'very low' in record.message
                   for record in caplog.records)

    def test_low_max_size_triggers_warning(self, caplog):
        """Test that very low max size triggers a warning."""
        with caplog.at_level(logging.WARNING):
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MIN_SIZE': '2',
                'DB_POOL_MAX_SIZE': '4'
            }):
                Settings()

        assert any('DB_POOL_MAX_SIZE' in record.message and 'very low' in record.message
                   for record in caplog.records)

    def test_very_high_min_size_triggers_warning(self, caplog):
        """Test that very high min size (>100) triggers a warning."""
        with caplog.at_level(logging.WARNING):
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MIN_SIZE': '150',
                'DB_POOL_MAX_SIZE': '200'
            }, clear=True):
                Settings()

        # Check that a warning was logged about high min size
        assert any(
            'DB_POOL_MIN_SIZE' in record.message and
            ('very high' in record.message or 'Typical production' in record.message)
            for record in caplog.records
        )

    def test_very_high_max_size_triggers_warning(self, caplog):
        """Test that very high max size (>500) triggers a warning."""
        with caplog.at_level(logging.WARNING):
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MIN_SIZE': '50',
                'DB_POOL_MAX_SIZE': '600'
            }, clear=True):
                Settings()

        # Check that a warning was logged about high max size
        assert any(
            'DB_POOL_MAX_SIZE' in record.message and
            ('very high' in record.message or '>500 connections' in record.message)
            for record in caplog.records
        )

    def test_production_level_sizes_no_warning(self, caplog):
        """Test that production-level sizes (20-100) don't trigger warnings."""
        with caplog.at_level(logging.WARNING):
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MIN_SIZE': '15',
                'DB_POOL_MAX_SIZE': '60'
            }):
                Settings()

        # Should not have pool size warnings
        pool_warnings = [
            record for record in caplog.records
            if 'DB_POOL' in record.message and 'very high' in record.message
        ]
        assert len(pool_warnings) == 0


class TestPoolConfigurationLogging:
    """Test that pool configuration is logged at startup."""

    def test_pool_config_logged_at_startup(self, caplog):
        """Test that pool configuration is logged in startup info."""
        with caplog.at_level(logging.INFO):
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MIN_SIZE': '10',
                'DB_POOL_MAX_SIZE': '50'
            }):
                settings = Settings()
                settings.log_startup_info()

        # Check that pool configuration was logged
        log_messages = [record.message for record in caplog.records]
        pool_log = [msg for msg in log_messages if 'Database Pool' in msg]

        assert len(pool_log) > 0
        assert any('min=10' in msg and 'max=50' in msg for msg in pool_log)

    def test_startup_logging_includes_database_url(self, caplog):
        """Test that startup logging includes truncated database URL."""
        with caplog.at_level(logging.INFO):
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:password@host.example.com/database',
                'GEMINI_API_KEY': 'test-key'
            }):
                settings = Settings()
                settings.log_startup_info()

        log_messages = [record.message for record in caplog.records]

        # Database URL should be logged but truncated for security
        db_logs = [msg for msg in log_messages if 'Database:' in msg]
        assert len(db_logs) > 0
        # Should be truncated (first 30 chars + ...)
        assert any('postgresql://' in msg and '...' in msg for msg in db_logs)
        # Should NOT contain full password
        assert not any('password@host.example.com' in msg for msg in log_messages)


class TestPoolSizeBoundaries:
    """Test pool size boundary conditions."""

    def test_min_size_at_lower_bound(self):
        """Test min size at lower boundary (1)."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'GEMINI_API_KEY': 'test-key',
            'DB_POOL_MIN_SIZE': '1',
            'DB_POOL_MAX_SIZE': '20'
        }):
            settings = Settings()
            assert settings.DB_POOL_MIN_SIZE == 1

    def test_max_size_at_upper_bound(self):
        """Test max size at upper boundary (100)."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'GEMINI_API_KEY': 'test-key',
            'DB_POOL_MIN_SIZE': '10',
            'DB_POOL_MAX_SIZE': '100'
        }):
            settings = Settings()
            assert settings.DB_POOL_MAX_SIZE == 100

    def test_min_size_exceeds_field_constraint(self):
        """Test that min size above field constraint (>1000) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MIN_SIZE': '1001',
                'DB_POOL_MAX_SIZE': '1100'
            }):
                Settings()

        assert 'DB_POOL_MIN_SIZE' in str(exc_info.value)

    def test_max_size_exceeds_field_constraint(self):
        """Test that max size above field constraint (>1000) is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            with patch.dict('os.environ', {
                'DATABASE_URL': 'postgresql://user:pass@localhost/db',
                'GEMINI_API_KEY': 'test-key',
                'DB_POOL_MIN_SIZE': '20',
                'DB_POOL_MAX_SIZE': '1001'
            }):
                Settings()

        assert 'DB_POOL_MAX_SIZE' in str(exc_info.value)


class TestProductionPoolRecommendations:
    """Test that production-recommended pool sizes work correctly."""

    def test_small_application_pool_sizes(self):
        """Test recommended sizes for small application (<10 req/sec)."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'GEMINI_API_KEY': 'test-key',
            'DB_POOL_MIN_SIZE': '5',
            'DB_POOL_MAX_SIZE': '20'
        }):
            settings = Settings()
            assert settings.DB_POOL_MIN_SIZE == 5
            assert settings.DB_POOL_MAX_SIZE == 20

    def test_medium_application_pool_sizes(self):
        """Test recommended sizes for medium application (10-100 req/sec)."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'GEMINI_API_KEY': 'test-key',
            'DB_POOL_MIN_SIZE': '10',
            'DB_POOL_MAX_SIZE': '50'
        }):
            settings = Settings()
            assert settings.DB_POOL_MIN_SIZE == 10
            assert settings.DB_POOL_MAX_SIZE == 50

    def test_large_application_pool_sizes(self):
        """Test recommended sizes for large application (100-1000 req/sec)."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'GEMINI_API_KEY': 'test-key',
            'DB_POOL_MIN_SIZE': '20',
            'DB_POOL_MAX_SIZE': '80'
        }):
            settings = Settings()
            assert settings.DB_POOL_MIN_SIZE == 20
            assert settings.DB_POOL_MAX_SIZE == 80

    def test_very_large_application_pool_sizes(self):
        """Test recommended sizes for very large application (>1000 req/sec)."""
        with patch.dict('os.environ', {
            'DATABASE_URL': 'postgresql://user:pass@localhost/db',
            'GEMINI_API_KEY': 'test-key',
            'DB_POOL_MIN_SIZE': '30',
            'DB_POOL_MAX_SIZE': '100'
        }):
            settings = Settings()
            assert settings.DB_POOL_MIN_SIZE == 30
            assert settings.DB_POOL_MAX_SIZE == 100
