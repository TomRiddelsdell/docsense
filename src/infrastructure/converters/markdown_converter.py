from pathlib import Path

from .base import (
    DocumentConverter,
    ConversionResult,
    DocumentMetadata,
    DocumentFormat,
)


class MarkdownConverter(DocumentConverter):
    
    @property
    def supported_extensions(self) -> list[str]:
        return ["md", "markdown", "mdown", "mkd"]
    
    def convert(self, file_path: Path) -> ConversionResult:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.convert_from_bytes(content.encode('utf-8'), file_path.name)
        except FileNotFoundError:
            return ConversionResult(
                success=False,
                markdown_content="",
                sections=[],
                metadata=DocumentMetadata(original_format=DocumentFormat.MARKDOWN),
                errors=[f"File not found: {file_path}"]
            )
        except UnicodeDecodeError as e:
            return ConversionResult(
                success=False,
                markdown_content="",
                sections=[],
                metadata=DocumentMetadata(original_format=DocumentFormat.MARKDOWN),
                errors=[f"Encoding error: {str(e)}"]
            )
    
    def convert_from_bytes(self, content: bytes, filename: str) -> ConversionResult:
        errors = []
        warnings = []
        
        try:
            markdown_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                markdown_content = content.decode('latin-1')
                warnings.append("Document was decoded using latin-1 fallback")
            except Exception as e:
                return ConversionResult(
                    success=False,
                    markdown_content="",
                    sections=[],
                    metadata=DocumentMetadata(original_format=DocumentFormat.MARKDOWN),
                    errors=[f"Failed to decode content: {str(e)}"]
                )
        
        title = self._extract_title(markdown_content) or filename
        
        metadata = DocumentMetadata(
            title=title,
            page_count=max(1, len(markdown_content) // 3000),
            word_count=self._count_words(markdown_content),
            original_format=DocumentFormat.MARKDOWN
        )
        
        sections = self._extract_sections(markdown_content)
        
        return ConversionResult(
            success=True,
            markdown_content=markdown_content,
            sections=sections,
            metadata=metadata,
            errors=errors,
            warnings=warnings
        )
    
    def _extract_title(self, markdown: str) -> str | None:
        lines = markdown.strip().split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return None
