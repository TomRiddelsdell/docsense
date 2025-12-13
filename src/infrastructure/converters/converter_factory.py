"""
Document converter factory for selecting and using appropriate converters.

The converter factory delegates to specific converters based on file extension.
Custom exceptions from converters are propagated to the caller for proper handling.

Possible exceptions:
- InvalidFileFormatError: File is not a valid document or is corrupted
- PasswordProtectedError: Document is password protected
- FileTooLargeError: File exceeds size limits
- EncodingError: Text encoding issues
- UnsupportedFileFormatError: File format not supported
"""
from pathlib import Path
import logging

from .base import DocumentConverter, ConversionResult, DocumentMetadata, DocumentFormat
from .word_converter import WordConverter
from .pdf_converter import PdfConverter
from .rst_converter import RstConverter
from .markdown_converter import MarkdownConverter
from .exceptions import (
    ConverterError,
    UnsupportedFileFormatError,
)

logger = logging.getLogger(__name__)


class ConverterFactory:
    
    def __init__(self):
        self._converters: list[DocumentConverter] = [
            WordConverter(),
            PdfConverter(),
            RstConverter(),
            MarkdownConverter(),
        ]
    
    def get_converter(self, file_path: Path) -> DocumentConverter | None:
        for converter in self._converters:
            if converter.can_convert(file_path):
                return converter
        return None
    
    def get_converter_for_extension(self, extension: str) -> DocumentConverter | None:
        ext = extension.lower().lstrip('.')
        for converter in self._converters:
            if ext in converter.supported_extensions:
                return converter
        return None
    
    def convert(self, file_path: Path) -> ConversionResult:
        """
        Convert a document file to markdown.

        Args:
            file_path: Path to the document file

        Returns:
            ConversionResult with markdown content and metadata

        Raises:
            UnsupportedFileFormatError: If file format is not supported
            InvalidFileFormatError: If file is corrupted or invalid
            PasswordProtectedError: If document is password protected
            FileTooLargeError: If file exceeds size limits
            EncodingError: If text encoding cannot be determined
        """
        converter = self.get_converter(file_path)
        if not converter:
            logger.error(f"Unsupported file format: {file_path.suffix}")
            raise UnsupportedFileFormatError(
                f"No converter available for file type: {file_path.suffix}",
                details={
                    'supported_formats': list(self.supported_formats.keys()),
                    'filename': str(file_path),
                    'extension': file_path.suffix
                }
            )

        logger.info(f"Converting {file_path.name} using {converter.__class__.__name__}")
        return converter.convert(file_path)

    def convert_from_bytes(self, content: bytes, filename: str) -> ConversionResult:
        """
        Convert document content (as bytes) to markdown.

        Args:
            content: Document content as bytes
            filename: Original filename (used to determine format)

        Returns:
            ConversionResult with markdown content and metadata

        Raises:
            UnsupportedFileFormatError: If file format is not supported
            InvalidFileFormatError: If file is corrupted or invalid
            PasswordProtectedError: If document is password protected
            FileTooLargeError: If file exceeds size limits
            EncodingError: If text encoding cannot be determined
        """
        path = Path(filename)
        converter = self.get_converter(path)
        if not converter:
            logger.error(f"Unsupported file format: {path.suffix}")
            raise UnsupportedFileFormatError(
                f"No converter available for file type: {path.suffix}",
                details={
                    'supported_formats': list(self.supported_formats.keys()),
                    'filename': filename,
                    'extension': path.suffix
                }
            )

        logger.info(f"Converting {filename} ({len(content)} bytes) using {converter.__class__.__name__}")
        return converter.convert_from_bytes(content, filename)
    
    @property
    def supported_extensions(self) -> list[str]:
        extensions = []
        for converter in self._converters:
            extensions.extend(converter.supported_extensions)
        return extensions
    
    @property
    def supported_formats(self) -> dict[str, list[str]]:
        return {
            "Word Documents": ["docx", "doc"],
            "PDF Documents": ["pdf"],
            "reStructuredText": ["rst", "rest"],
            "Markdown": ["md", "markdown", "mdown", "mkd"],
        }
