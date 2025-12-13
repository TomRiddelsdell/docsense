"""
Tests for input validation utilities.

Tests file upload validation, filename sanitization, and input validation to ensure
security vulnerabilities are prevented.
"""
import pytest
from fastapi import HTTPException, status

from src.api.utils.validation import (
    validate_file_size,
    validate_content_type,
    sanitize_filename,
    validate_title,
    validate_description,
    validate_upload_file,
    MAX_TITLE_LENGTH,
    MAX_DESCRIPTION_LENGTH,
    MAX_FILENAME_LENGTH,
)


class TestFileSizeValidation:
    """Tests for file size validation."""

    def test_file_size_within_limit(self):
        """Test that file size within limit passes validation."""
        # Should not raise
        validate_file_size(file_size=5000000, max_size=10485760)  # 5MB < 10MB

    def test_file_size_at_limit(self):
        """Test that file size exactly at limit passes validation."""
        # Should not raise
        validate_file_size(file_size=10485760, max_size=10485760)

    def test_file_size_exceeds_limit(self):
        """Test that file size exceeding limit raises exception."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_size(file_size=15000000, max_size=10485760)  # 15MB > 10MB

        assert exc_info.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        assert "exceeds maximum allowed size" in str(exc_info.value.detail).lower()

    def test_error_message_includes_sizes(self):
        """Test that error message includes both actual and maximum sizes."""
        with pytest.raises(HTTPException) as exc_info:
            validate_file_size(file_size=20000000, max_size=10485760)

        detail = str(exc_info.value.detail)
        assert "20,000,000" in detail or "20000000" in detail
        assert "10,485,760" in detail or "10485760" in detail or "10.0MB" in detail


class TestContentTypeValidation:
    """Tests for content type validation."""

    def test_pdf_content_type_allowed(self):
        """Test that PDF content type is allowed."""
        # Should not raise
        validate_content_type("application/pdf", "document.pdf")

    def test_docx_content_type_allowed(self):
        """Test that DOCX content type is allowed."""
        # Should not raise
        validate_content_type(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "document.docx"
        )

    def test_doc_content_type_allowed(self):
        """Test that DOC content type is allowed."""
        # Should not raise
        validate_content_type("application/msword", "document.doc")

    def test_markdown_content_type_allowed(self):
        """Test that Markdown content type is allowed."""
        # Should not raise
        validate_content_type("text/markdown", "document.md")

    def test_rst_content_type_allowed(self):
        """Test that RST content type is allowed."""
        # Should not raise
        validate_content_type("text/x-rst", "document.rst")

    def test_unsupported_content_type_rejected(self):
        """Test that unsupported content types are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_content_type("application/x-executable", "malicious.exe")

        assert exc_info.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        assert "not supported" in str(exc_info.value.detail).lower()

    def test_executable_content_type_rejected(self):
        """Test that executable content types are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_content_type("application/x-msdownload", "virus.exe")

        assert exc_info.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    def test_none_content_type_rejected(self):
        """Test that None content type is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_content_type(None)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "required" in str(exc_info.value.detail).lower()

    def test_content_type_with_charset_normalized(self):
        """Test that content types with charset parameters are normalized."""
        # Should not raise - charset should be stripped
        validate_content_type("application/pdf; charset=utf-8", "document.pdf")

    def test_mismatched_extension_rejected(self):
        """Test that mismatched extensions are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_content_type("application/pdf", "document.exe")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "extension" in str(exc_info.value.detail).lower()


class TestFilenameSanitization:
    """Tests for filename sanitization."""

    def test_simple_filename_unchanged(self):
        """Test that simple valid filenames are unchanged."""
        assert sanitize_filename("document.pdf") == "document.pdf"
        assert sanitize_filename("spec.docx") == "spec.docx"
        assert sanitize_filename("README.md") == "README.md"

    def test_filename_with_spaces(self):
        """Test that filenames with spaces are preserved."""
        assert sanitize_filename("my document.pdf") == "my document.pdf"
        assert sanitize_filename("final version (2).docx") == "final version (2).docx"

    def test_path_traversal_rejected(self):
        """Test that path traversal attempts are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename("../../../etc/passwd")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "path separators" in str(exc_info.value.detail).lower() or "parent directory" in str(exc_info.value.detail).lower()

    def test_forward_slash_rejected(self):
        """Test that forward slashes are rejected."""
        with pytest.raises(HTTPException):
            sanitize_filename("path/to/file.pdf")

    def test_backslash_rejected(self):
        """Test that backslashes are rejected."""
        with pytest.raises(HTTPException):
            sanitize_filename("path\\to\\file.pdf")

    def test_null_bytes_removed(self):
        """Test that null bytes are removed."""
        # This should succeed after removing null bytes
        result = sanitize_filename("document\x00.pdf")
        assert result == "document.pdf"
        assert "\x00" not in result

    def test_control_characters_removed(self):
        """Test that control characters are removed."""
        result = sanitize_filename("document\x01\x02\x03.pdf")
        assert result == "document.pdf"

    def test_leading_dots_stripped(self):
        """Test that leading dots are stripped."""
        assert sanitize_filename(".document.pdf") == "document.pdf"
        assert sanitize_filename("..document.pdf") == "document.pdf"

    def test_trailing_dots_stripped(self):
        """Test that trailing dots are stripped."""
        # Note: This will fail validation because after stripping trailing dots,
        # there might be no extension
        with pytest.raises(HTTPException):
            sanitize_filename("document...")

    def test_empty_filename_rejected(self):
        """Test that empty filenames are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename("")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "required" in str(exc_info.value.detail).lower()

    def test_none_filename_rejected(self):
        """Test that None filename is rejected."""
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename(None)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_filename_too_long_rejected(self):
        """Test that filenames exceeding max length are rejected."""
        long_filename = "x" * (MAX_FILENAME_LENGTH + 1) + ".pdf"
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename(long_filename)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "maximum length" in str(exc_info.value.detail).lower()

    def test_filename_without_extension_rejected(self):
        """Test that filenames without extension are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            sanitize_filename("document")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "extension" in str(exc_info.value.detail).lower()

    def test_multiple_dots_collapsed(self):
        """Test that multiple consecutive dots are collapsed."""
        result = sanitize_filename("document...final.pdf")
        assert result == "document.final.pdf"


class TestTitleValidation:
    """Tests for title validation."""

    def test_valid_title_accepted(self):
        """Test that valid titles are accepted."""
        # Should not raise
        validate_title("Trading Algorithm Specification")
        validate_title("A" * MAX_TITLE_LENGTH)  # At max length

    def test_empty_title_rejected(self):
        """Test that empty titles are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_title("")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "required" in str(exc_info.value.detail).lower()

    def test_whitespace_only_title_rejected(self):
        """Test that whitespace-only titles are rejected."""
        with pytest.raises(HTTPException):
            validate_title("   ")

    def test_none_title_rejected(self):
        """Test that None title is rejected."""
        with pytest.raises(HTTPException):
            validate_title(None)

    def test_title_too_long_rejected(self):
        """Test that titles exceeding max length are rejected."""
        long_title = "x" * (MAX_TITLE_LENGTH + 1)
        with pytest.raises(HTTPException) as exc_info:
            validate_title(long_title)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "maximum length" in str(exc_info.value.detail).lower()
        assert str(MAX_TITLE_LENGTH) in str(exc_info.value.detail)


class TestDescriptionValidation:
    """Tests for description validation."""

    def test_valid_description_accepted(self):
        """Test that valid descriptions are accepted."""
        # Should not raise
        validate_description("A comprehensive specification")
        validate_description("x" * MAX_DESCRIPTION_LENGTH)  # At max length

    def test_none_description_accepted(self):
        """Test that None description is accepted (optional)."""
        # Should not raise
        validate_description(None)

    def test_empty_description_accepted(self):
        """Test that empty description is accepted (optional)."""
        # Should not raise
        validate_description("")

    def test_description_too_long_rejected(self):
        """Test that descriptions exceeding max length are rejected."""
        long_description = "x" * (MAX_DESCRIPTION_LENGTH + 1)
        with pytest.raises(HTTPException) as exc_info:
            validate_description(long_description)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "maximum length" in str(exc_info.value.detail).lower()
        assert str(MAX_DESCRIPTION_LENGTH) in str(exc_info.value.detail)


class TestComprehensiveValidation:
    """Tests for comprehensive upload validation."""

    def test_valid_upload_passes_all_checks(self):
        """Test that valid upload passes all validation checks."""
        sanitized = validate_upload_file(
            filename="document.pdf",
            content_type="application/pdf",
            file_size=5000000,
            max_size=10485760,
            title="Trading Algorithm Spec",
            description="A comprehensive specification"
        )

        assert sanitized == "document.pdf"

    def test_invalid_filename_fails_early(self):
        """Test that invalid filename fails before other checks."""
        with pytest.raises(HTTPException) as exc_info:
            validate_upload_file(
                filename="../../../etc/passwd",
                content_type="application/pdf",
                file_size=5000000,
                max_size=10485760,
                title="Valid Title",
                description="Valid description"
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "path separators" in str(exc_info.value.detail).lower() or "parent directory" in str(exc_info.value.detail).lower()

    def test_invalid_content_type_fails(self):
        """Test that invalid content type fails validation."""
        with pytest.raises(HTTPException) as exc_info:
            validate_upload_file(
                filename="malicious.exe",
                content_type="application/x-executable",
                file_size=5000000,
                max_size=10485760,
                title="Valid Title",
                description="Valid description"
            )

        assert exc_info.value.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE

    def test_file_too_large_fails(self):
        """Test that file size exceeding limit fails validation."""
        with pytest.raises(HTTPException) as exc_info:
            validate_upload_file(
                filename="document.pdf",
                content_type="application/pdf",
                file_size=20000000,  # 20MB
                max_size=10485760,   # 10MB
                title="Valid Title",
                description="Valid description"
            )

        assert exc_info.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def test_invalid_title_fails(self):
        """Test that invalid title fails validation."""
        with pytest.raises(HTTPException) as exc_info:
            validate_upload_file(
                filename="document.pdf",
                content_type="application/pdf",
                file_size=5000000,
                max_size=10485760,
                title="",  # Empty title
                description="Valid description"
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "title" in str(exc_info.value.detail).lower()

    def test_invalid_description_fails(self):
        """Test that invalid description fails validation."""
        with pytest.raises(HTTPException) as exc_info:
            validate_upload_file(
                filename="document.pdf",
                content_type="application/pdf",
                file_size=5000000,
                max_size=10485760,
                title="Valid Title",
                description="x" * (MAX_DESCRIPTION_LENGTH + 1)
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "description" in str(exc_info.value.detail).lower()

    def test_sanitizes_filename(self):
        """Test that filename is properly sanitized."""
        sanitized = validate_upload_file(
            filename=".document.pdf",  # Leading dot
            content_type="application/pdf",
            file_size=5000000,
            max_size=10485760,
            title="Valid Title",
            description=None
        )

        assert sanitized == "document.pdf"
        assert not sanitized.startswith(".")
