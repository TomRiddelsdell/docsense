from pathlib import Path
import re

from docutils.core import publish_parts
from docutils.parsers.rst import Parser

from .base import (
    DocumentConverter,
    ConversionResult,
    DocumentMetadata,
    DocumentFormat,
)


class RstConverter(DocumentConverter):
    
    @property
    def supported_extensions(self) -> list[str]:
        return ["rst", "rest"]
    
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
                metadata=DocumentMetadata(original_format=DocumentFormat.RST),
                errors=[f"File not found: {file_path}"]
            )
        except UnicodeDecodeError as e:
            return ConversionResult(
                success=False,
                markdown_content="",
                sections=[],
                metadata=DocumentMetadata(original_format=DocumentFormat.RST),
                errors=[f"Encoding error: {str(e)}"]
            )
    
    def convert_from_bytes(self, content: bytes, filename: str) -> ConversionResult:
        errors = []
        warnings = []
        
        try:
            rst_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                rst_content = content.decode('latin-1')
                warnings.append("Document was decoded using latin-1 fallback")
            except Exception as e:
                return ConversionResult(
                    success=False,
                    markdown_content="",
                    sections=[],
                    metadata=DocumentMetadata(original_format=DocumentFormat.RST),
                    errors=[f"Failed to decode content: {str(e)}"]
                )
        
        markdown_content = self._rst_to_markdown(rst_content)
        
        title = self._extract_rst_title(rst_content)
        
        metadata = DocumentMetadata(
            title=title or filename,
            page_count=max(1, len(rst_content) // 3000),
            word_count=self._count_words(markdown_content),
            original_format=DocumentFormat.RST
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
    
    def _rst_to_markdown(self, rst_content: str) -> str:
        lines = rst_content.split('\n')
        markdown_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if self._is_underline(next_line):
                    level = self._get_heading_level(next_line[0])
                    markdown_lines.append(f"{'#' * level} {line.strip()}")
                    i += 2
                    continue
            
            if i > 0:
                prev_line = lines[i - 1]
                if self._is_underline(line) and prev_line.strip():
                    i += 1
                    continue
            
            if line.strip().startswith('.. code-block::'):
                lang = line.split('::')[-1].strip() or ""
                markdown_lines.append(f"```{lang}")
                i += 1
                while i < len(lines) and (lines[i].startswith('   ') or not lines[i].strip()):
                    if lines[i].strip():
                        markdown_lines.append(lines[i][3:] if lines[i].startswith('   ') else lines[i])
                    else:
                        markdown_lines.append("")
                    i += 1
                markdown_lines.append("```")
                continue
            
            line = re.sub(r'\*\*(.+?)\*\*', r'**\1**', line)
            line = re.sub(r'\*(.+?)\*', r'*\1*', line)
            line = re.sub(r'``(.+?)``', r'`\1`', line)
            line = re.sub(r':ref:`(.+?)`', r'[\1](#\1)', line)
            line = re.sub(r':doc:`(.+?)`', r'[\1](\1)', line)
            
            markdown_lines.append(line)
            i += 1
        
        return '\n'.join(markdown_lines)
    
    def _is_underline(self, line: str) -> bool:
        if not line.strip():
            return False
        char = line.strip()[0]
        return char in '=-~^"+' and len(set(line.strip())) == 1 and len(line.strip()) >= 3
    
    def _get_heading_level(self, char: str) -> int:
        levels = {'=': 1, '-': 2, '~': 3, '^': 4, '"': 5, '+': 6}
        return levels.get(char, 2)
    
    def _extract_rst_title(self, rst_content: str) -> str | None:
        lines = rst_content.split('\n')
        for i, line in enumerate(lines):
            if i + 1 < len(lines) and self._is_underline(lines[i + 1]):
                return line.strip()
        return None
