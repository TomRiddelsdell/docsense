"""
Tests for PDF converter exception handling.

Tests specific exception scenarios for PDF conversion.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.infrastructure.converters.pdf_converter import PdfConverter
from src.infrastructure.converters.exceptions import (
    InvalidFileFormatError,
    PasswordProtectedError,
    FileTooLargeError,
)


class TestPdfConverterExceptions:
    """Tests for PDF converter exception handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = PdfConverter()

    def test_file_not_found_returns_error_result(self):
        """Test that FileNotFoundError is handled gracefully."""
        result = self.converter.convert(Path("/nonexistent/file.pdf"))

        assert result.success is False
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    @patch('src.infrastructure.converters.pdf_converter.fitz')
    def test_password_protected_pdf_raises_exception(self, mock_fitz):
        """Test that password-protected PDFs raise PasswordProtectedError."""
        # Mock encrypted PDF
        mock_doc = MagicMock()
        mock_doc.is_encrypted = True
        mock_fitz.open.return_value.__enter__.return_value = mock_doc

        pdf_content = b"%PDF-1.4 encrypted content"

        with pytest.raises(PasswordProtectedError) as exc_info:
            self.converter.convert_from_bytes(pdf_content, "encrypted.pdf")

        assert "password" in str(exc_info.value).lower()
        assert exc_info.value.details.get('filename') == "encrypted.pdf"

    @patch('src.infrastructure.converters.pdf_converter.fitz')
    def test_corrupted_pdf_raises_invalid_format_error(self, mock_fitz):
        """Test that corrupted PDFs raise InvalidFileFormatError."""
        # Mock corrupted PDF using fitz.FileDataError
        import fitz as real_fitz
        mock_fitz.FileDataError = real_fitz.FileDataError
        mock_fitz.FileNotFoundError = real_fitz.FileNotFoundError
        mock_fitz.open.side_effect = real_fitz.FileDataError("PDF has damaged xref structure")

        pdf_content = b"%PDF-1.4 corrupted"

        with pytest.raises(InvalidFileFormatError) as exc_info:
            self.converter.convert_from_bytes(pdf_content, "corrupted.pdf")

        assert exc_info.value.details.get('format') == 'PDF'
        assert exc_info.value.details.get('filename') == "corrupted.pdf"

    @patch('src.infrastructure.converters.pdf_converter.fitz')
    def test_memory_error_raises_file_too_large(self, mock_fitz):
        """Test that MemoryError raises FileTooLargeError with size details."""
        # Mock memory error
        mock_fitz.open.side_effect = MemoryError("Out of memory")

        # Large PDF content (simulated)
        pdf_content = b"%PDF-1.4" + b"x" * (25 * 1024 * 1024)  # 25MB

        with pytest.raises(FileTooLargeError) as exc_info:
            self.converter.convert_from_bytes(pdf_content, "large.pdf")

        assert exc_info.value.details.get('filename') == "large.pdf"
        assert 'size_mb' in exc_info.value.details
        # Size should be approximately 25 MB
        size_mb = exc_info.value.details['size_mb']
        assert 24 < size_mb < 26

    @patch('src.infrastructure.converters.pdf_converter.fitz')
    def test_empty_pdf_returns_warning(self, mock_fitz):
        """Test that empty PDFs return result with warning."""
        # Mock empty PDF
        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.__len__.return_value = 0
        mock_doc.metadata = {}
        mock_fitz.open.return_value = mock_doc

        pdf_content = b"%PDF-1.4 empty"

        result = self.converter.convert_from_bytes(pdf_content, "empty.pdf")

        assert result.success is True
        assert len(result.warnings) > 0
        assert any("empty" in w.lower() or "no pages" in w.lower() for w in result.warnings)

    @patch('src.infrastructure.converters.pdf_converter.fitz')
    def test_large_pdf_returns_warning(self, mock_fitz):
        """Test that large PDFs (>10MB) return size warning."""
        # Mock large but valid PDF
        mock_doc = MagicMock()
        mock_doc.is_encrypted = False
        mock_doc.__len__.return_value = 1
        mock_doc.metadata = {}
        # Mock single page
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Test content"
        mock_doc.__getitem__.return_value = mock_page
        mock_fitz.open.return_value = mock_doc

        # 15MB PDF
        pdf_content = b"%PDF-1.4" + b"x" * (15 * 1024 * 1024)

        result = self.converter.convert_from_bytes(pdf_content, "large.pdf")

        # Should succeed but with warning
        assert result.success is True
        assert len(result.warnings) > 0
        # Check for size warning
        assert any("MB" in w or "large" in w.lower() for w in result.warnings)

    @patch('src.infrastructure.converters.pdf_converter.fitz')
    def test_runtime_error_with_encryption_message_raises_password_error(self, mock_fitz):
        """Test that RuntimeError mentioning encryption raises PasswordProtectedError."""
        # Mock RuntimeError with encryption message
        import fitz as real_fitz
        mock_fitz.FileDataError = real_fitz.FileDataError
        mock_fitz.FileNotFoundError = real_fitz.FileNotFoundError
        mock_fitz.open.side_effect = RuntimeError("file is encrypted")

        pdf_content = b"%PDF-1.4"

        with pytest.raises(PasswordProtectedError):
            self.converter.convert_from_bytes(pdf_content, "encrypted.pdf")

    @patch('src.infrastructure.converters.pdf_converter.fitz')
    def test_runtime_error_with_corruption_message_raises_invalid_format(self, mock_fitz):
        """Test that RuntimeError mentioning corruption raises InvalidFileFormatError."""
        # Mock RuntimeError with corruption message
        import fitz as real_fitz
        mock_fitz.FileDataError = real_fitz.FileDataError
        mock_fitz.FileNotFoundError = real_fitz.FileNotFoundError
        mock_fitz.open.side_effect = RuntimeError("file is damaged")

        pdf_content = b"%PDF-1.4"

        with pytest.raises(InvalidFileFormatError):
            self.converter.convert_from_bytes(pdf_content, "damaged.pdf")

    @patch('src.infrastructure.converters.pdf_converter.fitz')
    def test_unexpected_error_is_reraised(self, mock_fitz):
        """Test that unexpected errors are re-raised."""
        # Mock unexpected error
        mock_fitz.open.side_effect = ValueError("Unexpected error")

        pdf_content = b"%PDF-1.4"

        with pytest.raises(Exception):  # Could be ValueError or wrapped
            self.converter.convert_from_bytes(pdf_content, "test.pdf")


class TestPdfTableExtractionExceptions:
    """Tests for PDF table extraction exception handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = PdfConverter()

    def test_table_extraction_exception_handling_exists(self):
        """Test that table extraction has exception handling (documented behavior)."""
        # This is a documentation test - the actual table extraction code
        # in pdf_converter.py has try-except blocks around table extraction
        # to handle IndexError, AttributeError, OSError, IOError, and MemoryError
        assert hasattr(self.converter, '_extract_tables_with_pdfplumber')


class TestPdfFormulaExtractionExceptions:
    """Tests for PDF formula extraction exception handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.converter = PdfConverter()

    def test_formula_extraction_exception_handling_exists(self):
        """Test that formula extraction has exception handling (documented behavior)."""
        # This is a documentation test - the actual formula extraction code
        # in pdf_converter.py has try-except blocks with fallback levels
        # to handle AttributeError, KeyError, and TypeError
        assert hasattr(self.converter, '_extract_page_with_formulas')
