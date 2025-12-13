"""
Tests for custom converter exceptions.

Tests exception creation, user messages, and details handling.
"""
import pytest
from src.infrastructure.converters.exceptions import (
    ConverterError,
    FileNotReadableError,
    InvalidFileFormatError,
    UnsupportedFileFormatError,
    EncodingError,
    FileTooLargeError,
    ContentExtractionError,
    PasswordProtectedError,
    DependencyError,
)


class TestConverterError:
    """Tests for base ConverterError."""

    def test_base_exception_creation(self):
        """Test creating base exception with message and details."""
        error = ConverterError("Test error", details={'key': 'value'})

        assert error.message == "Test error"
        assert error.details == {'key': 'value'}
        assert str(error) == "Test error"

    def test_base_exception_without_details(self):
        """Test creating base exception without details."""
        error = ConverterError("Test error")

        assert error.message == "Test error"
        assert error.details == {}

    def test_base_exception_user_message(self):
        """Test base exception returns message as user message."""
        error = ConverterError("Test error")

        assert error.get_user_message() == "Test error"


class TestFileNotReadableError:
    """Tests for FileNotReadableError."""

    def test_creation(self):
        """Test creating file not readable error."""
        error = FileNotReadableError(
            "Cannot read file",
            details={'filename': 'test.pdf', 'reason': 'Permission denied'}
        )

        assert error.message == "Cannot read file"
        assert error.details['filename'] == 'test.pdf'
        assert error.details['reason'] == 'Permission denied'

    def test_user_message(self):
        """Test user message includes actionable solutions."""
        error = FileNotReadableError("Cannot read file")
        message = error.get_user_message()

        assert "Cannot read file" in message
        assert "file permissions" in message
        assert "not open in another program" in message
        assert "not corrupted" in message


class TestInvalidFileFormatError:
    """Tests for InvalidFileFormatError."""

    def test_creation(self):
        """Test creating invalid file format error."""
        error = InvalidFileFormatError(
            "File is corrupted",
            details={'format': 'PDF', 'filename': 'test.pdf'}
        )

        assert error.message == "File is corrupted"
        assert error.details['format'] == 'PDF'

    def test_user_message_with_format(self):
        """Test user message includes format information."""
        error = InvalidFileFormatError(
            "File is corrupted",
            details={'format': 'PDF'}
        )
        message = error.get_user_message()

        assert "File is corrupted" in message
        assert "valid PDF" in message
        assert "re-saving the file" in message

    def test_user_message_without_format(self):
        """Test user message without format details."""
        error = InvalidFileFormatError("File is corrupted")
        message = error.get_user_message()

        assert "valid document" in message


class TestUnsupportedFileFormatError:
    """Tests for UnsupportedFileFormatError."""

    def test_creation(self):
        """Test creating unsupported file format error."""
        error = UnsupportedFileFormatError(
            "File type not supported",
            details={
                'extension': '.xyz',
                'supported_formats': ['PDF', 'DOCX', 'MD']
            }
        )

        assert error.message == "File type not supported"
        assert error.details['extension'] == '.xyz'

    def test_user_message_with_supported_formats(self):
        """Test user message includes supported formats."""
        error = UnsupportedFileFormatError(
            "File type not supported",
            details={'supported_formats': ['PDF', 'DOCX', 'MD']}
        )
        message = error.get_user_message()

        assert "File type not supported" in message
        assert "PDF, DOCX, MD" in message
        assert "Convert the file" in message

    def test_user_message_without_supported_formats(self):
        """Test user message without supported formats."""
        error = UnsupportedFileFormatError("File type not supported")
        message = error.get_user_message()

        assert "File type not supported" in message


class TestEncodingError:
    """Tests for EncodingError."""

    def test_creation(self):
        """Test creating encoding error."""
        error = EncodingError(
            "Cannot decode file",
            details={
                'encoding': 'UTF-8',
                'filename': 'test.md',
                'tried_encodings': ['utf-8', 'latin-1', 'cp1252']
            }
        )

        assert error.message == "Cannot decode file"
        assert error.details['encoding'] == 'UTF-8'
        assert len(error.details['tried_encodings']) == 3

    def test_user_message_with_encoding(self):
        """Test user message includes encoding information."""
        error = EncodingError(
            "Cannot decode file",
            details={'encoding': 'UTF-8'}
        )
        message = error.get_user_message()

        assert "Cannot decode file" in message
        assert "UTF-8" in message
        assert "Save the file with UTF-8 encoding" in message

    def test_user_message_without_encoding(self):
        """Test user message without encoding details."""
        error = EncodingError("Cannot decode file")
        message = error.get_user_message()

        assert "UTF-8" in message  # Default encoding


class TestFileTooLargeError:
    """Tests for FileTooLargeError."""

    def test_creation(self):
        """Test creating file too large error."""
        error = FileTooLargeError(
            "File exceeds size limit",
            details={
                'size_mb': 25.5,
                'limit_mb': 20.0,
                'filename': 'large.pdf'
            }
        )

        assert error.message == "File exceeds size limit"
        assert error.details['size_mb'] == 25.5
        assert error.details['limit_mb'] == 20.0

    def test_user_message_with_sizes(self):
        """Test user message includes size information."""
        error = FileTooLargeError(
            "File exceeds size limit",
            details={'size_mb': 25.5, 'limit_mb': 20.0}
        )
        message = error.get_user_message()

        assert "File exceeds size limit" in message
        assert "25.5 MB" in message
        assert "20.0 MB" in message
        assert "Split the document" in message

    def test_user_message_without_sizes(self):
        """Test user message without size details."""
        error = FileTooLargeError("File exceeds size limit")
        message = error.get_user_message()

        assert "0.0 MB" in message  # Default values


class TestContentExtractionError:
    """Tests for ContentExtractionError."""

    def test_creation(self):
        """Test creating content extraction error."""
        error = ContentExtractionError(
            "Failed to extract tables",
            details={'content_type': 'tables', 'page': 5}
        )

        assert error.message == "Failed to extract tables"
        assert error.details['content_type'] == 'tables'

    def test_user_message_with_content_type(self):
        """Test user message includes content type."""
        error = ContentExtractionError(
            "Failed to extract tables",
            details={'content_type': 'tables'}
        )
        message = error.get_user_message()

        assert "Failed to extract tables" in message
        assert "extract tables" in message
        assert "incomplete conversion" in message

    def test_user_message_without_content_type(self):
        """Test user message without content type."""
        error = ContentExtractionError("Failed to extract")
        message = error.get_user_message()

        assert "extract content" in message  # Default content type


class TestPasswordProtectedError:
    """Tests for PasswordProtectedError."""

    def test_creation(self):
        """Test creating password protected error."""
        error = PasswordProtectedError(
            "Document is encrypted",
            details={'filename': 'secret.pdf', 'format': 'PDF'}
        )

        assert error.message == "Document is encrypted"
        assert error.details['filename'] == 'secret.pdf'

    def test_user_message(self):
        """Test user message includes solutions."""
        error = PasswordProtectedError("Document is encrypted")
        message = error.get_user_message()

        assert "Document is encrypted" in message
        assert "password protected" in message
        assert "Remove password protection" in message
        assert "not currently supported" in message


class TestDependencyError:
    """Tests for DependencyError."""

    def test_creation(self):
        """Test creating dependency error."""
        error = DependencyError(
            "Library not found",
            details={'library': 'pdfplumber', 'version_required': '0.5.0'}
        )

        assert error.message == "Library not found"
        assert error.details['library'] == 'pdfplumber'

    def test_user_message_with_library(self):
        """Test user message includes library name."""
        error = DependencyError(
            "Library not found",
            details={'library': 'pdfplumber'}
        )
        message = error.get_user_message()

        assert "Library not found" in message
        assert "pdfplumber" in message
        assert "pip install pdfplumber" in message

    def test_user_message_without_library(self):
        """Test user message without library details."""
        error = DependencyError("Library not found")
        message = error.get_user_message()

        assert "library" in message  # Default library name


class TestExceptionInheritance:
    """Tests for exception inheritance."""

    def test_all_exceptions_inherit_from_converter_error(self):
        """Test all custom exceptions inherit from ConverterError."""
        exceptions = [
            FileNotReadableError("test"),
            InvalidFileFormatError("test"),
            UnsupportedFileFormatError("test"),
            EncodingError("test"),
            FileTooLargeError("test"),
            ContentExtractionError("test"),
            PasswordProtectedError("test"),
            DependencyError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, ConverterError)
            assert isinstance(exc, Exception)

    def test_all_exceptions_have_user_message_method(self):
        """Test all exceptions implement get_user_message."""
        exceptions = [
            FileNotReadableError("test"),
            InvalidFileFormatError("test"),
            UnsupportedFileFormatError("test"),
            EncodingError("test"),
            FileTooLargeError("test"),
            ContentExtractionError("test"),
            PasswordProtectedError("test"),
            DependencyError("test"),
        ]

        for exc in exceptions:
            assert hasattr(exc, 'get_user_message')
            assert callable(exc.get_user_message)
            message = exc.get_user_message()
            assert isinstance(message, str)
            assert len(message) > 0
