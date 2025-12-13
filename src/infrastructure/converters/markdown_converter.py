from pathlib import Path
import logging

from .base import (
    DocumentConverter,
    ConversionResult,
    DocumentMetadata,
    DocumentFormat,
)
from .exceptions import EncodingError

logger = logging.getLogger(__name__)


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
            logger.error(f"Encoding error reading Markdown file {file_path}: {e}")
            raise EncodingError(
                f"File is not valid UTF-8: {e.reason}",
                details={'encoding': 'UTF-8', 'filename': str(file_path), 'position': e.start}
            )

        except PermissionError as e:
            logger.error(f"Permission denied reading file {file_path}: {e}")
            raise FileNotFoundError(f"Cannot read file (permission denied): {file_path}")

        except Exception as e:
            logger.exception(f"Unexpected error reading Markdown file {file_path}: {e}")
            raise
    
    def convert_from_bytes(self, content: bytes, filename: str) -> ConversionResult:
        errors = []
        warnings = []

        try:
            markdown_content = content.decode('utf-8')

        except UnicodeDecodeError as e:
            # Try fallback encodings
            logger.warning(f"UTF-8 decoding failed for {filename}, trying fallback encodings")

            try:
                markdown_content = content.decode('latin-1')
                warnings.append("Document was decoded using latin-1 fallback (may have character issues)")
                logger.info(f"Successfully decoded {filename} using latin-1")

            except UnicodeDecodeError:
                try:
                    markdown_content = content.decode('cp1252')  # Windows encoding
                    warnings.append("Document was decoded using cp1252 fallback (may have character issues)")
                    logger.info(f"Successfully decoded {filename} using cp1252")

                except UnicodeDecodeError as final_error:
                    logger.error(f"All encoding attempts failed for {filename}")
                    raise EncodingError(
                        "Cannot decode file with UTF-8, latin-1, or cp1252",
                        details={
                            'encoding': 'UTF-8',
                            'filename': filename,
                            'tried_encodings': ['utf-8', 'latin-1', 'cp1252'],
                            'error': str(final_error)
                        }
                    )

        except Exception as e:
            logger.exception(f"Unexpected error decoding {filename}: {e}")
            raise
        
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
