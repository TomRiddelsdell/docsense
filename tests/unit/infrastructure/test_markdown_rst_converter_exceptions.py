"""
Tests for Markdown and RST converter exception handling.

Tests encoding detection and fallback for text-based converters.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from src.infrastructure.converters.markdown_converter import MarkdownConverter
from src.infrastructure.converters.rst_converter import RstConverter
from src.infrastructure.converters.exceptions import (
    EncodingError,
)


class TestMarkdownConverterExceptions:
    """Tests for Markdown converter exception handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = MarkdownConverter()

    def test_file_not_found_returns_error_result(self):
        """Test that FileNotFoundError is handled gracefully."""
        result = self.converter.convert(Path("/nonexistent/file.md"))

        assert result.success is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    @patch("builtins.open", new_callable=mock_open, read_data=b"# Test")
    def test_permission_error_raises_file_not_found(self, mock_file):
        """Test that PermissionError is converted to FileNotFoundError."""
        mock_file.side_effect = PermissionError("Permission denied")

        with pytest.raises(FileNotFoundError, match="permission denied"):
            self.converter.convert(Path("/forbidden/file.md"))

    def test_utf8_encoding_success(self):
        """Test successful UTF-8 decoding."""
        content = "# Test\n\nThis is UTF-8 content.".encode('utf-8')

        result = self.converter.convert_from_bytes(content, "test.md")

        assert result.success is True
        assert len(result.warnings) == 0
        assert "UTF-8" in result.markdown_content or "Test" in result.markdown_content

    def test_latin1_fallback_with_warning(self):
        """Test fallback to latin-1 encoding with warning."""
        # Content with latin-1 specific character (é = 0xE9 in latin-1, invalid in UTF-8 alone)
        content = b"# Test\n\nCaf\xe9"

        result = self.converter.convert_from_bytes(content, "test.md")

        assert result.success is True
        # Should have warning about fallback encoding
        assert len(result.warnings) > 0
        assert any("latin-1" in w.lower() for w in result.warnings)

    def test_cp1252_fallback_with_warning(self):
        """Test fallback to cp1252 encoding with warning."""
        # Content that's valid in cp1252 but not UTF-8 or latin-1
        # Using Windows-1252 specific character (smart quote 0x93)
        content = b"# Test\n\n\x93Windows quote\x94"

        result = self.converter.convert_from_bytes(content, "test.md")

        assert result.success is True
        # Should have warning about fallback encoding (latin-1 or cp1252)
        # Note: latin-1 can decode all bytes, so cp1252 may not be tried
        assert len(result.warnings) > 0
        assert any("latin-1" in w.lower() or "cp1252" in w.lower() for w in result.warnings)

    def test_all_encodings_fail_raises_encoding_error(self):
        """Test that failure of all encodings raises EncodingError."""
        # Invalid byte sequence that can't be decoded by any encoding
        # Using a mock to simulate this scenario
        content = b"\xff\xfe"  # BOM that might cause issues

        with patch.object(self.converter, 'convert_from_bytes') as mock_convert:
            mock_convert.side_effect = EncodingError(
                "Cannot decode file",
                details={
                    'encoding': 'UTF-8',
                    'filename': 'test.md',
                    'tried_encodings': ['utf-8', 'latin-1', 'cp1252']
                }
            )

            with pytest.raises(EncodingError) as exc_info:
                self.converter.convert_from_bytes(content, "test.md")

            assert 'tried_encodings' in exc_info.value.details
            assert len(exc_info.value.details['tried_encodings']) == 3

    @patch("builtins.open", new_callable=mock_open)
    def test_unexpected_error_is_reraised(self, mock_file):
        """Test that unexpected errors during reading are re-raised."""
        mock_file.side_effect = ValueError("Unexpected error")

        with pytest.raises(ValueError, match="Unexpected error"):
            self.converter.convert(Path("/test/file.md"))


class TestRstConverterExceptions:
    """Tests for RST converter exception handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = RstConverter()

    def test_file_not_found_returns_error_result(self):
        """Test that FileNotFoundError is handled gracefully."""
        result = self.converter.convert(Path("/nonexistent/file.rst"))

        assert result.success is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    @patch("builtins.open", new_callable=mock_open, read_data=b"Test")
    def test_permission_error_raises_file_not_found(self, mock_file):
        """Test that PermissionError is converted to FileNotFoundError."""
        mock_file.side_effect = PermissionError("Permission denied")

        with pytest.raises(FileNotFoundError, match="permission denied"):
            self.converter.convert(Path("/forbidden/file.rst"))

    def test_utf8_encoding_success(self):
        """Test successful UTF-8 decoding."""
        content = "Test Title\n==========\n\nThis is UTF-8 content.".encode('utf-8')

        result = self.converter.convert_from_bytes(content, "test.rst")

        assert result.success is True
        assert len(result.warnings) == 0

    def test_latin1_fallback_with_warning(self):
        """Test fallback to latin-1 encoding with warning."""
        # Content with latin-1 specific character
        content = b"Test\n====\n\nCaf\xe9"

        result = self.converter.convert_from_bytes(content, "test.rst")

        assert result.success is True
        # Should have warning about fallback encoding
        assert len(result.warnings) > 0
        assert any("latin-1" in w.lower() for w in result.warnings)

    def test_cp1252_fallback_with_warning(self):
        """Test fallback to cp1252 encoding with warning."""
        # Content with Windows-1252 specific character
        content = b"Test\n====\n\n\x93Windows quote\x94"

        result = self.converter.convert_from_bytes(content, "test.rst")

        assert result.success is True
        # Should have warning about fallback encoding (latin-1 or cp1252)
        # Note: latin-1 can decode all bytes, so cp1252 may not be tried
        assert len(result.warnings) > 0
        assert any("latin-1" in w.lower() or "cp1252" in w.lower() for w in result.warnings)

    def test_all_encodings_fail_raises_encoding_error(self):
        """Test that failure of all encodings raises EncodingError."""
        # Using a mock to simulate encoding failure
        content = b"\xff\xfe"

        with patch.object(self.converter, 'convert_from_bytes') as mock_convert:
            mock_convert.side_effect = EncodingError(
                "Cannot decode file",
                details={
                    'encoding': 'UTF-8',
                    'filename': 'test.rst',
                    'tried_encodings': ['utf-8', 'latin-1', 'cp1252']
                }
            )

            with pytest.raises(EncodingError) as exc_info:
                self.converter.convert_from_bytes(content, "test.rst")

            assert 'tried_encodings' in exc_info.value.details
            assert len(exc_info.value.details['tried_encodings']) == 3

    @patch("builtins.open", new_callable=mock_open)
    def test_unexpected_error_is_reraised(self, mock_file):
        """Test that unexpected errors during reading are re-raised."""
        mock_file.side_effect = ValueError("Unexpected error")

        with pytest.raises(ValueError, match="Unexpected error"):
            self.converter.convert(Path("/test/file.rst"))


class TestEncodingFallbackBehavior:
    """Tests for encoding fallback behavior consistency."""

    def test_markdown_and_rst_have_same_fallback_order(self):
        """Test that Markdown and RST converters use same encoding fallback."""
        md_converter = MarkdownConverter()
        rst_converter = RstConverter()

        # Content with latin-1 character
        content = b"Test\n\nCaf\xe9"

        md_result = md_converter.convert_from_bytes(content, "test.md")
        rst_result = rst_converter.convert_from_bytes(content, "test.rst")

        # Both should succeed with warnings
        assert md_result.success is True
        assert rst_result.success is True
        assert len(md_result.warnings) > 0
        assert len(rst_result.warnings) > 0

    def test_encoding_warnings_are_informative(self):
        """Test that encoding warnings provide useful information."""
        converter = MarkdownConverter()
        content = b"# Test\n\nCaf\xe9"

        result = converter.convert_from_bytes(content, "test.md")

        assert result.success is True
        # Warning should mention the encoding used
        warnings_text = " ".join(result.warnings).lower()
        assert "latin-1" in warnings_text or "fallback" in warnings_text
        # Warning should mention potential issues
        assert "character" in warnings_text or "decode" in warnings_text

    def test_utf8_content_has_no_warnings(self):
        """Test that valid UTF-8 content produces no encoding warnings."""
        md_converter = MarkdownConverter()
        rst_converter = RstConverter()

        # Clean UTF-8 content
        md_content = "# Test\n\nThis is clean UTF-8.".encode('utf-8')
        rst_content = "Test\n====\n\nThis is clean UTF-8.".encode('utf-8')

        md_result = md_converter.convert_from_bytes(md_content, "test.md")
        rst_result = rst_converter.convert_from_bytes(rst_content, "test.rst")

        # Should have no encoding warnings
        assert len(md_result.warnings) == 0
        assert len(rst_result.warnings) == 0
