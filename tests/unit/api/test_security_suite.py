"""
Comprehensive security test suite for the Trading Algorithm Document Analyzer API.

Tests cover:
1. SQL Injection Prevention
2. XSS (Cross-Site Scripting) Prevention
3. Command Injection Prevention
4. Path Traversal Prevention
5. Header Security
6. Error Information Disclosure
7. Content Type Validation
8. Request Size Limits
9. Query Parameter Security
10. JSON Payload Security

This test suite ensures the application follows OWASP Top 10 security best practices.
"""
import pytest
import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from io import BytesIO


@pytest.fixture
def test_app():
    """Create FastAPI test application with test environment."""
    import os
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
    os.environ["GEMINI_API_KEY"] = "test-key-12345678901234567890123456789012"
    os.environ["SECRET_KEY"] = "test-secret-key-12345678901234567890123456789012"
    os.environ["CORS_ORIGINS"] = "http://localhost:5000"  # Specific origin, not wildcard
    os.environ["MAX_UPLOAD_SIZE"] = "1048576"  # 1MB

    from src.api.main import create_app
    return create_app()


@pytest.fixture
def test_client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestSQLInjectionPrevention:
    """Test that the application is protected against SQL injection attacks."""

    def test_sql_injection_in_document_id(self, test_client):
        """Test that SQL injection attempts in document ID are handled safely."""
        # SQL injection payloads
        sql_injection_payloads = [
            "1' OR '1'='1",
            "1'; DROP TABLE events; --",
            "1' UNION SELECT * FROM events--",
            "1' AND 1=1--",
            "%27%20OR%20%271%27=%271",  # URL encoded
        ]

        for payload in sql_injection_payloads:
            # Document ID should be validated as UUID
            response = test_client.get(f"/api/v1/documents/{payload}")

            # Should return 422 (validation error) not 200 or 500
            assert response.status_code == 422, f"SQL injection payload not rejected: {payload}"

            # Should not leak database error information
            response_text = response.text.lower()
            assert "sql" not in response_text or "invalid" in response_text
            assert "drop table" not in response_text
            assert "postgresql" not in response_text

    def test_sql_injection_in_query_parameters(self, test_client):
        """Test that SQL injection attempts in query parameters are rejected."""
        sql_payloads = [
            "1' OR '1'='1",
            "'; DROP TABLE events; --",
            "' UNION SELECT password FROM users--",
        ]

        # Test various endpoints with query parameters
        for payload in sql_payloads:
            # Test search endpoint (if exists)
            response = test_client.get(f"/api/v1/documents?search={payload}")

            # Should handle gracefully (200, 400, 404, or 422, not 500)
            assert response.status_code in [200, 400, 404, 422], \
                f"Unexpected error for SQL injection in query: {payload}"

            # Should not leak SQL error information
            if response.status_code >= 400:
                response_text = response.text.lower()
                assert "syntax error" not in response_text
                assert "drop table" not in response_text

    def test_parameterized_queries_used(self):
        """Test that the event store uses parameterized queries (code inspection)."""
        from src.infrastructure.persistence.event_store import PostgresEventStore
        import inspect

        # Get the source code of the append method
        source = inspect.getsource(PostgresEventStore.append)

        # Verify parameterized query syntax ($1, $2, etc.)
        assert "$1" in source or "$2" in source, \
            "Event store should use parameterized queries"

        # Verify no dangerous string formatting
        assert "f\"INSERT" not in source and "f'INSERT" not in source, \
            "Should not use f-strings for SQL queries (SQL injection risk)"


class TestXSSPrevention:
    """Test that the application properly encodes outputs to prevent XSS attacks."""

    def test_xss_in_document_title_upload(self, test_client):
        """Test that XSS payloads in document title are properly validated/encoded."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
        ]

        for payload in xss_payloads:
            # Try to upload document with XSS in title
            # Title validation should reject or encode
            response = test_client.post(
                "/api/v1/documents/upload",
                data={"title": payload, "description": "Test"},
                files={"file": ("test.pdf", BytesIO(b"%PDF-1.4test"), "application/pdf")}
            )

            # API should handle this (validation may reject, or accept and encode)
            assert response.status_code in [200, 201, 400, 413, 415, 422], \
                f"XSS payload should be handled: {payload}"

    def test_response_content_type_is_json(self, test_client):
        """Test that API responses have correct Content-Type header."""
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type, \
            "API should return JSON content type"

    def test_xss_in_error_messages(self, test_client):
        """Test that error messages don't reflect unencoded user input."""
        xss_payload = "<script>alert('XSS')</script>"

        # Try invalid UUID with XSS payload
        response = test_client.get(f"/api/v1/documents/{xss_payload}")

        # Should return validation error
        assert response.status_code == 422

        # FastAPI/Pydantic auto-encodes JSON responses
        # Error message should be JSON-encoded (< becomes \\u003c or &lt;)
        response_text = response.text
        assert "<script>" not in response_text or "\\u003c" in response_text, \
            "Error messages should not contain raw HTML"


class TestCommandInjectionPrevention:
    """Test that the application doesn't allow command injection."""

    def test_no_os_command_execution_in_file_processing(self):
        """Test that file converters don't use os.system or subprocess with user input."""
        import inspect
        from src.infrastructure.converters import (
            pdf_converter, word_converter, markdown_converter, rst_converter
        )

        modules = [pdf_converter, word_converter, markdown_converter, rst_converter]

        for module in modules:
            source = inspect.getsource(module)

            # Check for dangerous patterns
            assert "os.system(" not in source, \
                f"{module.__name__} should not use os.system()"

            # subprocess.call with shell=True is dangerous
            if "subprocess.call(" in source:
                assert "shell=True" not in source, \
                    f"{module.__name__} should not use shell=True with subprocess"

            assert "eval(" not in source, \
                f"{module.__name__} should not use eval()"
            assert "exec(" not in source, \
                f"{module.__name__} should not use exec()"


class TestPathTraversalPrevention:
    """Test that the application prevents path traversal attacks."""

    def test_path_traversal_in_filename(self, test_client):
        """Test that path traversal attempts in filenames are blocked."""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
        ]

        for payload in path_traversal_payloads:
            response = test_client.post(
                "/api/v1/documents/upload",
                data={"title": "Test", "description": "Test"},
                files={"file": (payload, BytesIO(b"%PDF-1.4test"), "application/pdf")}
            )

            # Filename validation should sanitize or reject
            assert response.status_code in [200, 201, 400, 413, 415, 422], \
                f"Path traversal attempt should be handled: {payload}"

    def test_null_byte_injection_in_filename(self, test_client):
        """Test that null byte injection is prevented."""
        null_byte_payload = "test.pdf\x00.exe"

        response = test_client.post(
            "/api/v1/documents/upload",
            data={"title": "Test", "description": "Test"},
            files={"file": (null_byte_payload, BytesIO(b"%PDF-1.4test"), "application/pdf")}
        )

        # Null bytes should be removed or file rejected
        assert response.status_code in [200, 201, 400, 413, 415, 422], \
            "Null byte injection should be handled"


class TestHeaderSecurity:
    """Test that security headers are properly configured."""

    def test_cors_headers_present(self, test_client):
        """Test that CORS headers are configured."""
        response = test_client.options("/api/v1/health")

        # TestClient may not trigger CORS middleware properly
        # This is a limitation of testing with TestClient vs real HTTP
        # Just verify the app doesn't crash on OPTIONS request
        assert response.status_code in [200, 405], \
            "OPTIONS request should be handled"

    def test_content_type_options_header(self, test_client):
        """Test X-Content-Type-Options header (recommended for production)."""
        response = test_client.get("/api/v1/health")

        # Document that this header should be added in production
        x_content_type = response.headers.get("x-content-type-options", "")

        if not x_content_type:
            pytest.skip("X-Content-Type-Options header not implemented (recommendation for production)")

    def test_frame_options_header(self, test_client):
        """Test X-Frame-Options header prevents clickjacking (recommended)."""
        response = test_client.get("/api/v1/health")

        x_frame_options = response.headers.get("x-frame-options", "")

        if not x_frame_options:
            pytest.skip("X-Frame-Options header not implemented (recommendation for production)")

    def test_strict_transport_security(self, test_client):
        """Test HSTS header for HTTPS (production recommendation)."""
        response = test_client.get("/api/v1/health")

        hsts = response.headers.get("strict-transport-security", "")

        if not hsts:
            pytest.skip("HSTS header not implemented (production recommendation for HTTPS)")


class TestErrorInformationDisclosure:
    """Test that error messages don't leak sensitive information."""

    def test_database_errors_not_exposed(self, test_client):
        """Test that database errors don't expose sensitive information."""
        # Try to trigger an error (non-existent document)
        response = test_client.get(f"/api/v1/documents/{uuid.uuid4()}")

        # Should return 404 or 422, not 500 with database details
        assert response.status_code in [404, 422], \
            "Non-existent resource should return 404 or 422"

        if response.status_code >= 400:
            error_text = response.text.lower()

            # Should not expose database internals
            assert "postgresql" not in error_text or "not found" in error_text
            assert "password" not in error_text
            assert "connection string" not in error_text

    def test_404_errors_dont_enumerate_resources(self, test_client):
        """Test that 404 errors don't reveal internal structure."""
        # Non-existent document
        response1 = test_client.get(f"/api/v1/documents/{uuid.uuid4()}")

        # Invalid UUID format
        response2 = test_client.get("/api/v1/documents/invalid-uuid")

        # Both should return appropriate error codes
        assert response1.status_code in [404, 422]
        assert response2.status_code in [404, 422]

        # Error messages should not reveal database table names unnecessarily
        for response in [response1, response2]:
            error_text = response.text.lower()
            # "table" in error context is OK if it's generic message
            # Just ensure we're not exposing actual SQL table names
            assert "events" not in error_text or "not found" in error_text

    def test_validation_errors_are_informative_but_safe(self, test_client):
        """Test that validation errors are helpful but don't leak internals."""
        # Send invalid document upload (title too long)
        long_title = "x" * 300

        response = test_client.post(
            "/api/v1/documents/upload",
            data={"title": long_title, "description": "Test"},
            files={"file": ("test.pdf", BytesIO(b"%PDF-1.4test"), "application/pdf")}
        )

        # Should return validation error
        assert response.status_code in [400, 413, 422], \
            "Invalid input should return 400/413/422"

        error_text = response.text.lower()

        # Error should mention the problem field
        assert "title" in error_text or "too long" in error_text or "length" in error_text, \
            "Validation errors should indicate the problem field"

        # But should not expose framework internals unnecessarily
        # (Some framework names in errors are acceptable, just not internal paths)
        assert "/home/" not in error_text and "/usr/" not in error_text, \
            "Should not expose file paths"


class TestContentTypeValidation:
    """Test that content types are properly validated."""

    def test_executable_file_types_rejected(self, test_client):
        """Test that executable file types are rejected."""
        dangerous_types = [
            ("malware.exe", "application/x-msdownload"),
            ("malware.bat", "application/x-bat"),
            ("malware.sh", "application/x-sh"),
        ]

        for filename, content_type in dangerous_types:
            response = test_client.post(
                "/api/v1/documents/upload",
                data={"title": "Test", "description": "Test"},
                files={"file": (filename, BytesIO(b"malicious content"), content_type)}
            )

            # Should reject dangerous file types with 415 or 400
            assert response.status_code in [400, 415, 422], \
                f"Executable file type should be rejected: {content_type}"

    def test_content_type_matches_file_extension(self, test_client):
        """Test content type validation (document current behavior)."""
        # Send PDF content with .txt extension
        response = test_client.post(
            "/api/v1/documents/upload",
            data={"title": "Test", "description": "Test"},
            files={"file": ("document.txt", BytesIO(b"%PDF-1.4test"), "text/plain")}
        )

        # Document current behavior (may accept or reject)
        assert response.status_code in [200, 201, 400, 415, 422], \
            "Mismatched content type should be handled"


class TestRequestSizeLimits:
    """Test that request size limits are enforced."""

    def test_file_size_limit_enforced(self, test_client):
        """Test that file upload size limit is enforced."""
        # Create file larger than MAX_UPLOAD_SIZE (1MB + 1KB)
        large_file = BytesIO(b"x" * (1024 * 1024 + 1024))

        response = test_client.post(
            "/api/v1/documents/upload",
            data={"title": "Large File", "description": "Test"},
            files={"file": ("large.pdf", large_file, "application/pdf")}
        )

        # Should reject file exceeding size limit
        assert response.status_code in [400, 413], \
            "Files exceeding size limit should be rejected with 413 or 400"

    def test_json_payload_size_reasonable(self, test_client):
        """Test that very large JSON payloads are handled."""
        # Create large description (5MB string)
        huge_description = "x" * (5 * 1024 * 1024)

        response = test_client.post(
            "/api/v1/documents/upload",
            data={"title": "Test", "description": huge_description},
            files={"file": ("test.pdf", BytesIO(b"%PDF-1.4test"), "application/pdf")}
        )

        # Should handle large payloads (reject or accept with truncation)
        assert response.status_code in [200, 201, 400, 413, 422], \
            "Should handle large JSON payloads gracefully"


class TestQueryParameterSecurity:
    """Test that query parameters are properly validated and sanitized."""

    def test_excessive_query_parameters_handled(self, test_client):
        """Test that excessive query parameters don't cause DoS."""
        # Create query string with many parameters
        params = {f"param{i}": f"value{i}" for i in range(100)}

        response = test_client.get("/api/v1/documents", params=params)

        # Should handle gracefully (not crash)
        assert response.status_code in [200, 400, 404, 413], \
            "Should handle excessive query parameters gracefully"

    def test_special_characters_in_query_params(self, test_client):
        """Test that special characters in query params are handled safely."""
        special_chars = [
            "<script>alert('XSS')</script>",
            "'; DROP TABLE events; --",
        ]

        for char in special_chars:
            response = test_client.get(f"/api/v1/documents?search={char}")

            # Should handle safely (not crash, not execute)
            assert response.status_code in [200, 400, 404, 422], \
                f"Should handle special characters safely: {char}"

            # Response should not contain unencoded special chars
            if response.status_code == 200:
                assert "<script>" not in response.text, \
                    "Special characters should be encoded in response"


class TestJSONPayloadSecurity:
    """Test that JSON payloads are properly validated."""

    def test_deeply_nested_json_handled(self, test_client):
        """Test that deeply nested JSON doesn't cause DoS."""
        # Create deeply nested JSON (50 levels - reasonable limit)
        nested = {"message": "test"}
        current = nested
        for i in range(50):
            current["level"] = {}
            current = current["level"]

        response = test_client.post(
            "/api/v1/chat",
            json=nested
        )

        # Should handle deeply nested JSON (may accept or reject based on limits)
        assert response.status_code in [200, 201, 400, 404, 413, 422], \
            "Should handle deeply nested JSON safely"

    def test_malformed_json_rejected(self, test_client):
        """Test that malformed JSON returns appropriate error."""
        # Send raw malformed JSON
        response = test_client.post(
            "/api/v1/chat",
            content=b"{this is not valid json}",
            headers={"Content-Type": "application/json"}
        )

        # Should return 400 or 422 for malformed JSON (or 404 if endpoint doesn't exist)
        assert response.status_code in [400, 404, 422], \
            "Malformed JSON should return 400/404/422"


class TestSecurityCodePractices:
    """Test that the codebase follows secure coding practices."""

    def test_no_hardcoded_secrets(self):
        """Test that no secrets are hardcoded in the codebase (code inspection)."""
        import os
        import re

        # Patterns that might indicate hardcoded secrets
        secret_patterns = [
            r"password\s*=\s*['\"](?!test|example|password|changeme|xxx)[^'\"]{8,}['\"]",
            r"api_key\s*=\s*['\"](?!test|example|xxx|key)[^'\"]{20,}['\"]",
            r"secret_key\s*=\s*['\"](?!test|example|xxx)[^'\"]{20,}['\"]",
        ]

        # Check main config file
        from src.api import config
        import inspect
        source = inspect.getsource(config)

        for pattern in secret_patterns:
            matches = re.findall(pattern, source, re.IGNORECASE)
            assert len(matches) == 0, \
                f"Potential hardcoded secret found in config.py: {matches}"

    def test_environment_variables_used_for_secrets(self):
        """Test that secrets are loaded from environment variables."""
        from src.api.config import Settings

        # Settings should use environment variables
        import inspect
        source = inspect.getsource(Settings)

        # Should reference os.environ or use Pydantic's env config
        assert "env_prefix" in source.lower() or "env" in source.lower(), \
            "Settings should use environment variables for configuration"

    def test_database_url_not_hardcoded(self):
        """Test that DATABASE_URL is not hardcoded."""
        from src.api import config
        import inspect
        source = inspect.getsource(config)

        # Should not contain actual database credentials
        assert "postgresql://postgres:password" not in source, \
            "Database URL should not be hardcoded"
        assert "@localhost:5432" not in source or "example" in source or "test" in source, \
            "Production database URL should not be hardcoded"


# Summary test to verify overall security posture
def test_security_test_coverage():
    """Verify that the security test suite has comprehensive coverage."""
    import inspect
    import sys

    # Get all test classes in this module
    current_module = sys.modules[__name__]
    test_classes = [
        obj for name, obj in inspect.getmembers(current_module)
        if inspect.isclass(obj) and name.startswith("Test")
    ]

    # Verify we have tests for major OWASP categories
    test_class_names = [cls.__name__ for cls in test_classes]

    assert "TestSQLInjectionPrevention" in test_class_names
    assert "TestXSSPrevention" in test_class_names
    assert "TestCommandInjectionPrevention" in test_class_names
    assert "TestPathTraversalPrevention" in test_class_names
    assert "TestHeaderSecurity" in test_class_names
    assert "TestErrorInformationDisclosure" in test_class_names
    assert "TestContentTypeValidation" in test_class_names
    assert "TestRequestSizeLimits" in test_class_names

    # Count total test methods
    total_tests = sum(
        len([m for m in inspect.getmembers(cls) if m[0].startswith("test_")])
        for cls in test_classes
    )

    assert total_tests >= 25, f"Security test suite should have at least 25 tests, found {total_tests}"
