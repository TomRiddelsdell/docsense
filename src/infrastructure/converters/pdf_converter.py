from pathlib import Path
from io import BytesIO
from typing import Any

import fitz
import pdfplumber

from .base import (
    DocumentConverter,
    ConversionResult,
    DocumentMetadata,
    DocumentFormat,
)


class PdfConverter(DocumentConverter):
    
    @property
    def supported_extensions(self) -> list[str]:
        return ["pdf"]
    
    def convert(self, file_path: Path) -> ConversionResult:
        try:
            with open(file_path, 'rb') as f:
                return self.convert_from_bytes(f.read(), file_path.name)
        except FileNotFoundError:
            return ConversionResult(
                success=False,
                markdown_content="",
                sections=[],
                metadata=DocumentMetadata(original_format=DocumentFormat.PDF),
                errors=[f"File not found: {file_path}"]
            )
    
    def convert_from_bytes(self, content: bytes, filename: str) -> ConversionResult:
        errors: list[str] = []
        warnings: list[str] = []
        doc: Any = None
        
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            
            markdown_lines: list[str] = []
            page_count = len(doc)
            
            for page_num in range(page_count):
                page = doc[page_num]
                text = page.get_text("text")
                
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        markdown_lines.append("")
                        continue
                    
                    if self._is_likely_heading(line):
                        level = self._guess_heading_level(line)
                        markdown_lines.append(f"{'#' * level} {line}")
                    else:
                        markdown_lines.append(line)
                
                if page_num < page_count - 1:
                    markdown_lines.append("")
                    markdown_lines.append("---")
                    markdown_lines.append("")
            
            pdf_metadata = doc.metadata if doc.metadata else {}
            
            metadata = DocumentMetadata(
                title=pdf_metadata.get("title", "") or filename,
                author=pdf_metadata.get("author"),
                created_date=pdf_metadata.get("creationDate"),
                modified_date=pdf_metadata.get("modDate"),
                page_count=page_count,
                word_count=0,
                original_format=DocumentFormat.PDF
            )
            
        except Exception as e:
            return ConversionResult(
                success=False,
                markdown_content="",
                sections=[],
                metadata=DocumentMetadata(original_format=DocumentFormat.PDF),
                errors=[f"Failed to process PDF: {str(e)}"]
            )
        finally:
            if doc:
                doc.close()
        
        table_content = self._extract_tables_with_pdfplumber(content, warnings)
        if table_content:
            markdown_lines.append("")
            markdown_lines.append("## Extracted Tables")
            markdown_lines.append("")
            markdown_lines.append(table_content)
        
        markdown_content = '\n'.join(markdown_lines)
        metadata.word_count = self._count_words(markdown_content)
        
        sections = self._extract_sections(markdown_content)
        
        return ConversionResult(
            success=True,
            markdown_content=markdown_content,
            sections=sections,
            metadata=metadata,
            errors=errors,
            warnings=warnings
        )
    
    def _is_likely_heading(self, line: str) -> bool:
        if len(line) > 100:
            return False
        if line.isupper() and len(line.split()) <= 10:
            return True
        if line.endswith(':') and len(line.split()) <= 8:
            return True
        return False
    
    def _guess_heading_level(self, line: str) -> int:
        words = len(line.split())
        if words <= 3:
            return 1
        elif words <= 6:
            return 2
        else:
            return 3
    
    def _extract_tables_with_pdfplumber(self, content: bytes, warnings: list[str]) -> str:
        table_markdown: list[str] = []
        
        try:
            with pdfplumber.open(BytesIO(content)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    for table_idx, table in enumerate(tables, 1):
                        if not table or not table[0]:
                            continue
                        
                        table_markdown.append(f"### Table {page_num}.{table_idx}")
                        table_markdown.append("")
                        
                        for row_idx, row in enumerate(table):
                            cells = [str(cell or '').strip().replace('\n', ' ') for cell in row]
                            table_markdown.append('| ' + ' | '.join(cells) + ' |')
                            if row_idx == 0:
                                table_markdown.append('| ' + ' | '.join(['---'] * len(cells)) + ' |')
                        
                        table_markdown.append("")
        except Exception as e:
            warnings.append(f"Could not extract tables: {str(e)}")
        
        return '\n'.join(table_markdown)
