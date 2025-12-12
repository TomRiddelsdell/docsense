from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from src.domain.value_objects.semantic_ir import DocumentIR


class DocumentFormat(Enum):
    WORD = "docx"
    PDF = "pdf"
    RST = "rst"
    MARKDOWN = "md"
    UNKNOWN = "unknown"


@dataclass
class DocumentSection:
    id: str
    title: str
    content: str
    level: int
    start_line: int | None = None
    end_line: int | None = None


@dataclass
class DocumentMetadata:
    title: str | None = None
    author: str | None = None
    created_date: str | None = None
    modified_date: str | None = None
    page_count: int = 0
    word_count: int = 0
    original_format: DocumentFormat = DocumentFormat.UNKNOWN
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversionResult:
    success: bool
    markdown_content: str
    sections: list[DocumentSection]
    metadata: DocumentMetadata
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    semantic_ir: Optional["DocumentIR"] = None  # Optional semantic IR


class DocumentConverter(ABC):
    
    @property
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        pass
    
    @abstractmethod
    def convert(self, file_path: Path) -> ConversionResult:
        pass
    
    @abstractmethod
    def convert_from_bytes(self, content: bytes, filename: str) -> ConversionResult:
        pass
    
    def can_convert(self, file_path: Path) -> bool:
        return file_path.suffix.lower().lstrip('.') in self.supported_extensions
    
    def _extract_sections(self, markdown: str) -> list[DocumentSection]:
        sections = []
        current_section = None
        current_content_lines = []
        section_id = 0
        
        lines = markdown.split('\n')
        for line_num, line in enumerate(lines, 1):
            if line.startswith('#'):
                if current_section:
                    current_section.content = '\n'.join(current_content_lines).strip()
                    current_section.end_line = line_num - 1
                    sections.append(current_section)
                
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                section_id += 1
                current_section = DocumentSection(
                    id=f"section-{section_id}",
                    title=title,
                    content="",
                    level=level,
                    start_line=line_num
                )
                current_content_lines = []
            elif current_section:
                current_content_lines.append(line)
        
        if current_section:
            current_section.content = '\n'.join(current_content_lines).strip()
            current_section.end_line = len(lines)
            sections.append(current_section)
        
        return sections
    
    def _count_words(self, text: str) -> int:
        return len(text.split())
