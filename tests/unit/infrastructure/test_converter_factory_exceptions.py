"""
Tests for converter factory exception handling.

Tests that converter factory raises appropriate exceptions for unsupported formats.
"""
import pytest
from pathlib import Path
from src.infrastructure.converters.converter_factory import ConverterFactory
from src.infrastructure.converters.exceptions import (
    UnsupportedFileFormatError,
)


class TestConverterFactoryExceptions:
    """Tests for converter factory exception handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = ConverterFactory()

    def test_unsupported_extension_raises_exception(self):
        """Test that unsupported file extensions raise UnsupportedFileFormatError."""
        unsupported_file = Path("/test/document.xyz")

        with pytest.raises(UnsupportedFileFormatError) as exc_info:
            self.factory.convert(unsupported_file)

        assert ".xyz" in str(exc_info.value)
        assert 'supported_formats' in exc_info.value.details
        assert 'extension' in exc_info.value.details
        assert exc_info.value.details['extension'] == '.xyz'

    def test_unsupported_extension_from_bytes_raises_exception(self):
        """Test that unsupported extensions in convert_from_bytes raise exception."""
        content = b"Some content"
        filename = "document.xyz"

        with pytest.raises(UnsupportedFileFormatError) as exc_info:
            self.factory.convert_from_bytes(content, filename)

        assert ".xyz" in str(exc_info.value)
        assert exc_info.value.details['extension'] == '.xyz'
        assert exc_info.value.details['filename'] == filename

    def test_exception_includes_supported_formats(self):
        """Test that exception details include list of supported formats."""
        with pytest.raises(UnsupportedFileFormatError) as exc_info:
            self.factory.convert(Path("/test/file.unknown"))

        supported = exc_info.value.details.get('supported_formats')
        assert supported is not None
        assert len(supported) > 0
        # Should include common formats
        all_formats = str(supported).lower()
        assert 'word' in all_formats or 'docx' in all_formats
        assert 'pdf' in all_formats
        assert 'markdown' in all_formats or 'md' in all_formats

    def test_exception_user_message_is_helpful(self):
        """Test that user message provides helpful information."""
        with pytest.raises(UnsupportedFileFormatError) as exc_info:
            self.factory.convert(Path("/test/file.txt"))

        user_message = exc_info.value.get_user_message()
        assert len(user_message) > 0
        # Should mention what formats are supported
        assert "supported" in user_message.lower() or "format" in user_message.lower()

    def test_supported_pdf_does_not_raise_unsupported_error(self):
        """Test that supported PDF format does not raise UnsupportedFileFormatError."""
        # Converters return ConversionResult with errors for non-existent files
        result = self.factory.convert(Path("/test/document.pdf"))
        # Should return a result (even if unsuccessful), not raise UnsupportedFileFormatError
        assert hasattr(result, 'success')

    def test_supported_docx_does_not_raise_unsupported_error(self):
        """Test that supported DOCX format does not raise UnsupportedFileFormatError."""
        result = self.factory.convert(Path("/test/document.docx"))
        assert hasattr(result, 'success')

    def test_supported_markdown_does_not_raise_unsupported_error(self):
        """Test that supported Markdown format does not raise UnsupportedFileFormatError."""
        result = self.factory.convert(Path("/test/document.md"))
        assert hasattr(result, 'success')

    def test_supported_rst_does_not_raise_unsupported_error(self):
        """Test that supported RST format does not raise UnsupportedFileFormatError."""
        result = self.factory.convert(Path("/test/document.rst"))
        assert hasattr(result, 'success')

    def test_case_insensitive_extension_handling(self):
        """Test that extensions are handled case-insensitively."""
        # Uppercase extension should work fine
        result = self.factory.convert(Path("/test/document.PDF"))
        # Should return a result, not raise UnsupportedFileFormatError
        assert hasattr(result, 'success')

    def test_get_converter_returns_none_for_unsupported(self):
        """Test that get_converter returns None for unsupported formats."""
        converter = self.factory.get_converter(Path("/test/file.xyz"))
        assert converter is None

    def test_get_converter_returns_converter_for_supported(self):
        """Test that get_converter returns converter for supported formats."""
        pdf_converter = self.factory.get_converter(Path("/test/file.pdf"))
        assert pdf_converter is not None

        docx_converter = self.factory.get_converter(Path("/test/file.docx"))
        assert docx_converter is not None

        md_converter = self.factory.get_converter(Path("/test/file.md"))
        assert md_converter is not None

        rst_converter = self.factory.get_converter(Path("/test/file.rst"))
        assert rst_converter is not None

    def test_get_converter_for_extension_handles_dot(self):
        """Test that get_converter_for_extension handles extensions with and without dot."""
        converter_with_dot = self.factory.get_converter_for_extension(".pdf")
        converter_without_dot = self.factory.get_converter_for_extension("pdf")

        assert converter_with_dot is not None
        assert converter_without_dot is not None
        assert type(converter_with_dot) == type(converter_without_dot)

    def test_supported_extensions_property(self):
        """Test that supported_extensions property returns all extensions."""
        extensions = self.factory.supported_extensions

        assert isinstance(extensions, list)
        assert len(extensions) > 0
        # Should include common extensions
        extensions_lower = [ext.lower() for ext in extensions]
        assert 'pdf' in extensions_lower
        assert 'docx' in extensions_lower
        assert 'md' in extensions_lower
        assert 'rst' in extensions_lower

    def test_supported_formats_property(self):
        """Test that supported_formats property returns format categories."""
        formats = self.factory.supported_formats

        assert isinstance(formats, dict)
        assert len(formats) > 0
        # Should have categories
        categories = list(formats.keys())
        assert any('pdf' in cat.lower() for cat in categories)
        assert any('word' in cat.lower() for cat in categories)
        assert any('markdown' in cat.lower() for cat in categories)


class TestConverterFactoryErrorPropagation:
    """Tests that converter factory properly propagates converter exceptions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = ConverterFactory()

    def test_converter_exceptions_are_propagated(self):
        """Test that exceptions from converters are propagated to caller."""
        from src.infrastructure.converters.exceptions import (
            InvalidFileFormatError,
            PasswordProtectedError,
            EncodingError,
        )
        from unittest.mock import patch, MagicMock

        # Mock a converter that raises InvalidFileFormatError
        mock_converter = MagicMock()
        mock_converter.can_convert.return_value = True
        mock_converter.convert.side_effect = InvalidFileFormatError(
            "Invalid PDF",
            details={'format': 'PDF'}
        )

        with patch.object(self.factory, '_converters', [mock_converter]):
            with pytest.raises(InvalidFileFormatError):
                self.factory.convert(Path("/test/file.pdf"))

    def test_password_protected_error_propagated(self):
        """Test that PasswordProtectedError is propagated from converters."""
        from src.infrastructure.converters.exceptions import PasswordProtectedError
        from unittest.mock import patch, MagicMock

        mock_converter = MagicMock()
        mock_converter.can_convert.return_value = True
        mock_converter.convert.side_effect = PasswordProtectedError(
            "Document is encrypted",
            details={'filename': 'test.pdf'}
        )

        with patch.object(self.factory, '_converters', [mock_converter]):
            with pytest.raises(PasswordProtectedError):
                self.factory.convert(Path("/test/file.pdf"))

    def test_encoding_error_propagated(self):
        """Test that EncodingError is propagated from converters."""
        from src.infrastructure.converters.exceptions import EncodingError
        from unittest.mock import patch, MagicMock

        mock_converter = MagicMock()
        mock_converter.can_convert.return_value = True
        mock_converter.convert_from_bytes.side_effect = EncodingError(
            "Cannot decode",
            details={'encoding': 'UTF-8'}
        )

        with patch.object(self.factory, '_converters', [mock_converter]):
            with pytest.raises(EncodingError):
                self.factory.convert_from_bytes(b"content", "test.md")


class TestConverterSelection:
    """Tests for converter selection logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = ConverterFactory()

    def test_pdf_files_use_pdf_converter(self):
        """Test that PDF files select PDF converter."""
        converter = self.factory.get_converter(Path("/test/file.pdf"))
        assert converter.__class__.__name__ == "PdfConverter"

    def test_docx_files_use_word_converter(self):
        """Test that DOCX files select Word converter."""
        converter = self.factory.get_converter(Path("/test/file.docx"))
        assert converter.__class__.__name__ == "WordConverter"

    def test_doc_files_use_word_converter(self):
        """Test that DOC files select Word converter."""
        converter = self.factory.get_converter(Path("/test/file.doc"))
        assert converter.__class__.__name__ == "WordConverter"

    def test_md_files_use_markdown_converter(self):
        """Test that MD files select Markdown converter."""
        converter = self.factory.get_converter(Path("/test/file.md"))
        assert converter.__class__.__name__ == "MarkdownConverter"

    def test_markdown_files_use_markdown_converter(self):
        """Test that .markdown files select Markdown converter."""
        converter = self.factory.get_converter(Path("/test/file.markdown"))
        assert converter.__class__.__name__ == "MarkdownConverter"

    def test_rst_files_use_rst_converter(self):
        """Test that RST files select RST converter."""
        converter = self.factory.get_converter(Path("/test/file.rst"))
        assert converter.__class__.__name__ == "RstConverter"

    def test_rest_files_use_rst_converter(self):
        """Test that .rest files select RST converter."""
        converter = self.factory.get_converter(Path("/test/file.rest"))
        assert converter.__class__.__name__ == "RstConverter"
