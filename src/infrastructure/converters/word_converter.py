from pathlib import Path
from io import BytesIO

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from .base import (
    DocumentConverter,
    ConversionResult,
    DocumentMetadata,
    DocumentFormat,
)


class WordConverter(DocumentConverter):
    
    @property
    def supported_extensions(self) -> list[str]:
        return ["docx", "doc"]
    
    def convert(self, file_path: Path) -> ConversionResult:
        try:
            with open(file_path, 'rb') as f:
                return self.convert_from_bytes(f.read(), file_path.name)
        except FileNotFoundError:
            return ConversionResult(
                success=False,
                markdown_content="",
                sections=[],
                metadata=DocumentMetadata(original_format=DocumentFormat.WORD),
                errors=[f"File not found: {file_path}"]
            )
    
    def convert_from_bytes(self, content: bytes, filename: str) -> ConversionResult:
        errors = []
        warnings = []
        
        try:
            doc = Document(BytesIO(content))
        except PackageNotFoundError:
            return ConversionResult(
                success=False,
                markdown_content="",
                sections=[],
                metadata=DocumentMetadata(original_format=DocumentFormat.WORD),
                errors=["Invalid or corrupted Word document"]
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                markdown_content="",
                sections=[],
                metadata=DocumentMetadata(original_format=DocumentFormat.WORD),
                errors=[f"Failed to open document: {str(e)}"]
            )
        
        markdown_lines = []
        
        for para in doc.paragraphs:
            style_name: str = para.style.name if para.style and para.style.name else ""
            text = para.text.strip()
            
            if not text:
                markdown_lines.append("")
                continue
            
            if "Heading 1" in style_name:
                markdown_lines.append(f"# {text}")
            elif "Heading 2" in style_name:
                markdown_lines.append(f"## {text}")
            elif "Heading 3" in style_name:
                markdown_lines.append(f"### {text}")
            elif "Heading 4" in style_name:
                markdown_lines.append(f"#### {text}")
            elif "Heading 5" in style_name:
                markdown_lines.append(f"##### {text}")
            elif "Heading 6" in style_name:
                markdown_lines.append(f"###### {text}")
            elif "List" in style_name:
                markdown_lines.append(f"- {text}")
            elif "Code" in style_name:
                markdown_lines.append(f"```\n{text}\n```")
            else:
                markdown_lines.append(text)
            
            markdown_lines.append("")
        
        for table in doc.tables:
            table_md = self._convert_table(table)
            markdown_lines.append(table_md)
            markdown_lines.append("")
        
        markdown_content = '\n'.join(markdown_lines)
        
        core_props = doc.core_properties
        metadata = DocumentMetadata(
            title=core_props.title or filename,
            author=core_props.author,
            created_date=str(core_props.created) if core_props.created else None,
            modified_date=str(core_props.modified) if core_props.modified else None,
            page_count=len(doc.sections),
            word_count=self._count_words(markdown_content),
            original_format=DocumentFormat.WORD
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
    
    def _convert_table(self, table) -> str:
        rows = []
        for row in table.rows:
            cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
            rows.append('| ' + ' | '.join(cells) + ' |')
        
        if len(rows) >= 1:
            header_sep = '| ' + ' | '.join(['---'] * len(table.rows[0].cells)) + ' |'
            rows.insert(1, header_sep)
        
        return '\n'.join(rows)
