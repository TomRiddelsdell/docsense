"""
Tests for CORS security middleware configuration.

These tests verify that the CORS middleware in main.py correctly implements
the security policy defined in Settings validation (already tested in test_config.py).

Note: Settings-level CORS validation is thoroughly tested in test_config.py.
These tests focus on the middleware configuration and runtime behavior.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.api.config import Settings


class TestCORSMiddlewareConfiguration:
    """Tests for CORS middleware setup in main.py."""

    @patch('src.api.config.get_settings')
    def test_middleware_disables_credentials_for_wildcard(self, mock_get_settings, caplog):
        """Test that middleware disables credentials when wildcard is used."""
        # Mock settings with wildcard CORS (development environment)
        mock_settings = MagicMock(spec=Settings)
        mock_settings.ENVIRONMENT = "development"
        mock_settings.get_cors_origins_list.return_value = ["*"]
        mock_settings.PORT = 8000
        mock_settings.ENABLE_DOCS = True
        mock_settings.API_BASE_PATH = "/api/v1"
        mock_get_settings.return_value = mock_settings

        from src.api.main import create_app
        app = create_app()

        # Should log that credentials are disabled
        log_messages = [record.message for record in caplog.records]
        assert any("CORS Security Error" in msg for msg in log_messages)
        assert any("allow_credentials disabled" in msg or "Allow Credentials: False" in msg for msg in log_messages)

    @patch('src.api.config.get_settings')
    def test_middleware_enables_credentials_for_specific_origins(self, mock_get_settings, caplog):
        """Test that middleware enables credentials for specific origins."""
        # Mock settings with specific origins
        mock_settings = MagicMock(spec=Settings)
        mock_settings.ENVIRONMENT = "production"
        mock_settings.get_cors_origins_list.return_value = ["https://app.example.com"]
        mock_settings.PORT = 8000
        mock_settings.ENABLE_DOCS = False
        mock_settings.API_BASE_PATH = "/api/v1"
        mock_get_settings.return_value = mock_settings

        import logging
        with caplog.at_level(logging.INFO):
            from src.api.main import create_app
            app = create_app()

        # Should log that credentials are enabled
        log_messages = [record.message for record in caplog.records]
        assert any("Allow Credentials: True" in msg for msg in log_messages)

    @patch('src.api.config.get_settings')
    def test_middleware_logs_cors_configuration(self, mock_get_settings, caplog):
        """Test that middleware logs CORS configuration at startup."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.ENVIRONMENT = "development"
        mock_settings.get_cors_origins_list.return_value = ["http://localhost:5000", "http://localhost:3000"]
        mock_settings.PORT = 8000
        mock_settings.ENABLE_DOCS = True
        mock_settings.API_BASE_PATH = "/api/v1"
        mock_get_settings.return_value = mock_settings

        import logging
        with caplog.at_level(logging.INFO):
            from src.api.main import create_app
            create_app()

        # Verify CORS configuration was logged
        log_messages = [record.message for record in caplog.records]
        assert any("CORS Configuration" in msg for msg in log_messages)
        assert any("Allowed Origins" in msg for msg in log_messages)
        assert any("Allow Credentials" in msg for msg in log_messages)


class TestCORSRuntimeBehavior:
    """Tests for CORS middleware runtime behavior."""

    @patch('src.api.config.get_settings')
    def test_cors_allows_configured_origin(self, mock_get_settings):
        """Test that requests from configured origins are allowed."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.ENVIRONMENT = "development"
        mock_settings.get_cors_origins_list.return_value = ["http://localhost:5000"]
        mock_settings.PORT = 8000
        mock_settings.ENABLE_DOCS = True
        mock_settings.API_BASE_PATH = "/api/v1"
        mock_get_settings.return_value = mock_settings

        from src.api.main import create_app
        app = create_app()
        client = TestClient(app)

        # Make a request with Origin header
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "http://localhost:5000"}
        )

        # Should succeed
        assert response.status_code == 200

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers

    @patch('src.api.config.get_settings')
    def test_cors_rejects_non_configured_origin(self, mock_get_settings):
        """Test that requests from non-configured origins don't get CORS headers."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.ENVIRONMENT = "production"
        mock_settings.get_cors_origins_list.return_value = ["https://app.example.com"]
        mock_settings.PORT = 8000
        mock_settings.ENABLE_DOCS = False
        mock_settings.API_BASE_PATH = "/api/v1"
        mock_get_settings.return_value = mock_settings

        from src.api.main import create_app
        app = create_app()
        client = TestClient(app)

        # Make a request with non-allowed Origin
        response = client.get(
            "/api/v1/health",
            headers={"Origin": "https://malicious-site.com"}
        )

        # Request succeeds (CORS is browser-enforced)
        assert response.status_code == 200

        # The access-control-allow-origin header should not be the malicious origin
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] != "https://malicious-site.com"

    @patch('src.api.config.get_settings')
    def test_cors_preflight_request_handled(self, mock_get_settings):
        """Test that CORS preflight OPTIONS requests are handled correctly."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.ENVIRONMENT = "development"
        mock_settings.get_cors_origins_list.return_value = ["http://localhost:5000"]
        mock_settings.PORT = 8000
        mock_settings.ENABLE_DOCS = True
        mock_settings.API_BASE_PATH = "/api/v1"
        mock_get_settings.return_value = mock_settings

        from src.api.main import create_app
        app = create_app()
        client = TestClient(app)

        # Make a preflight request
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
        )

        # Preflight should succeed
        assert response.status_code == 200

        # Should have CORS preflight headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers


class TestCORSDocumentation:
    """Tests to ensure CORS is properly documented."""

    def test_env_example_has_cors_documentation(self):
        """Test that .env.example has comprehensive CORS documentation."""
        env_example_path = "/workspaces/.env.example"

        with open(env_example_path, 'r') as f:
            content = f.read()

        # Verify CORS documentation exists
        assert "CORS_ORIGINS" in content
        assert "CORS allowed origins" in content or "CORS_ORIGINS" in content

        # Verify security warnings
        assert "wildcard" in content.lower() or "*" in content
        assert "security" in content.lower()

        # Verify examples
        assert "localhost" in content or "example.com" in content

    def test_cors_configuration_examples_valid(self):
        """Test that CORS configuration examples in .env.example are valid."""
        env_example_path = "/workspaces/.env.example"

        with open(env_example_path, 'r') as f:
            for line in f:
                if line.startswith("CORS_ORIGINS=") and not line.startswith("#"):
                    origins_value = line.split("=", 1)[1].strip()

                    # Should not be just a wildcard
                    if origins_value == "*":
                        pytest.fail("Default CORS_ORIGINS in .env.example should not be wildcard '*'")

                    # Should be comma-separated origins
                    if "," in origins_value:
                        origins = [o.strip() for o in origins_value.split(",")]
                        for origin in origins:
                            # Each origin should start with http:// or https://
                            assert origin.startswith("http://") or origin.startswith("https://"), \
                                f"CORS origin should include protocol: {origin}"
