from pathlib import Path

from .base import DocumentConverter, ConversionResult, DocumentMetadata, DocumentFormat
from .word_converter import WordConverter
from .pdf_converter import PdfConverter
from .rst_converter import RstConverter
from .markdown_converter import MarkdownConverter


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
        converter = self.get_converter(file_path)
        if not converter:
            return ConversionResult(
                success=False,
                markdown_content="",
                sections=[],
                metadata=DocumentMetadata(original_format=DocumentFormat.UNKNOWN),
                errors=[f"No converter available for file type: {file_path.suffix}"]
            )
        return converter.convert(file_path)
    
    def convert_from_bytes(self, content: bytes, filename: str) -> ConversionResult:
        path = Path(filename)
        converter = self.get_converter(path)
        if not converter:
            return ConversionResult(
                success=False,
                markdown_content="",
                sections=[],
                metadata=DocumentMetadata(original_format=DocumentFormat.UNKNOWN),
                errors=[f"No converter available for file type: {path.suffix}"]
            )
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
