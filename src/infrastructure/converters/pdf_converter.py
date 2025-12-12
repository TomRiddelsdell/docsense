from pathlib import Path
from io import BytesIO
from typing import Any, List, Dict
import re

import fitz
import pdfplumber

from .base import (
    DocumentConverter,
    ConversionResult,
    DocumentMetadata,
    DocumentFormat,
)


class PdfConverter(DocumentConverter):
    """
    Enhanced PDF converter with support for mathematical formulas.
    
    This converter detects mathematical notation (typically in CambriaMath or similar fonts)
    and converts them to LaTeX format for proper rendering in markdown viewers.
    """
    
    # Fonts commonly used for mathematical notation
    MATH_FONTS = {
        'CambriaMath', 'STIX', 'MathJax', 'SymbolMT', 'Symbol', 
        'MT Extra', 'Cambria-Math', 'Latin Modern Math'
    }
    
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
                
                # Use enhanced text extraction with formula detection
                page_markdown = self._extract_page_with_formulas(page, warnings)
                markdown_lines.extend(page_markdown)
                
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
    
    def _extract_page_with_formulas(self, page: Any, warnings: List[str]) -> List[str]:
        """
        Extract text from a PDF page while preserving mathematical formulas.
        
        This method uses the 'dict' extraction mode to analyze fonts and detect
        mathematical notation, converting it to LaTeX format.
        """
        markdown_lines: List[str] = []
        
        try:
            text_dict = page.get_text("dict")
            blocks = text_dict.get("blocks", [])
            
            for block in blocks:
                if block.get("type") != 0:  # Skip non-text blocks
                    continue
                
                lines = block.get("lines", [])
                if not lines:
                    continue
                
                # Check if this block contains mathematical notation
                block_text = self._extract_block_text(lines)
                is_math_block = self._is_mathematical_block(lines)
                
                if is_math_block:
                    # Convert mathematical block to LaTeX
                    latex_formula = self._convert_to_latex(lines)
                    if latex_formula:
                        # Use $$ for display math (block formulas)
                        markdown_lines.append("")
                        markdown_lines.append(f"$$")
                        markdown_lines.append(latex_formula)
                        markdown_lines.append(f"$$")
                        markdown_lines.append("")
                    else:
                        # Fallback to regular text if LaTeX conversion fails
                        markdown_lines.append(block_text)
                else:
                    # Regular text processing
                    if block_text.strip():
                        # Check if the first line is a heading
                        first_line = block_text.split('\n')[0]
                        if self._is_likely_heading(first_line):
                            level = self._guess_heading_level(first_line)
                            markdown_lines.append(f"{'#' * level} {first_line}")
                            # Add remaining lines if any
                            remaining = '\n'.join(block_text.split('\n')[1:]).strip()
                            if remaining:
                                markdown_lines.extend(remaining.split('\n'))
                        else:
                            # Add all lines from the block, preserving line breaks
                            markdown_lines.extend(block_text.split('\n'))
                    else:
                        markdown_lines.append("")
            
        except Exception as e:
            warnings.append(f"Error extracting formulas: {str(e)}")
            # Fallback to simple text extraction
            text = page.get_text("text")
            markdown_lines = text.split('\n')
        
        return markdown_lines
    
    def _extract_block_text(self, lines: List[Dict]) -> str:
        """Extract plain text from a block's lines, preserving line breaks."""
        line_texts = []
        for line in lines:
            span_texts = []
            for span in line.get("spans", []):
                span_texts.append(span.get("text", ""))
            line_text = "".join(span_texts).strip()
            if line_text:
                line_texts.append(line_text)
        return "\n".join(line_texts)
    
    def _is_mathematical_block(self, lines: List[Dict]) -> bool:
        """
        Determine if a block contains mathematical notation.
        
        A block is considered mathematical if:
        - It uses a mathematical font (CambriaMath, etc.)
        - It contains mathematical symbols (√, ∑, ∫, etc.)
        - It has a high density of subscripts/superscripts
        """
        if not lines:
            return False
        
        math_font_count = 0
        total_span_count = 0
        has_math_symbols = False
        small_font_count = 0  # Subscripts/superscripts often use smaller fonts
        
        for line in lines:
            for span in line.get("spans", []):
                total_span_count += 1
                font = span.get("font", "")
                text = span.get("text", "")
                size = span.get("size", 10)
                
                # Check for mathematical fonts
                if any(math_font in font for math_font in self.MATH_FONTS):
                    math_font_count += 1
                
                # Check for mathematical symbols
                math_symbols = {'√', '∑', '∫', '∏', '∂', '∆', '∇', '±', '≤', '≥', '≠', '≈', '∞', '×', '÷'}
                if any(sym in text for sym in math_symbols):
                    has_math_symbols = True
                
                # Check for smaller fonts (likely subscripts/superscripts)
                if size < 8:
                    small_font_count += 1
        
        if total_span_count == 0:
            return False
        
        # Consider it math if >50% uses math fonts or has math symbols
        math_font_ratio = math_font_count / total_span_count
        return math_font_ratio > 0.5 or has_math_symbols
    
    def _convert_to_latex(self, lines: List[Dict]) -> str:
        """
        Convert mathematical notation from PDF spans to LaTeX format.
        
        This handles:
        - Subscripts and superscripts (detected by font size)
        - Mathematical operators
        - Fractions (detected by spatial layout)
        - Greek letters and special symbols
        """
        latex_parts = []
        
        # Group spans by vertical position to detect fractions
        line_groups = self._group_spans_by_position(lines)
        
        if len(line_groups) > 1:
            # Potential fraction or multi-line formula
            latex_parts.append(self._build_complex_formula(line_groups))
        else:
            # Single-line formula
            for line in lines:
                line_latex = self._convert_line_to_latex(line)
                if line_latex:
                    latex_parts.append(line_latex)
        
        return " ".join(latex_parts).strip()
    
    def _group_spans_by_position(self, lines: List[Dict]) -> List[List[Dict]]:
        """Group spans by their vertical position to detect fractions."""
        groups = []
        for line in lines:
            spans = line.get("spans", [])
            if spans:
                groups.append(spans)
        return groups
    
    def _build_complex_formula(self, line_groups: List[List[Dict]]) -> str:
        """Build a complex formula (like fractions) from multiple line groups."""
        if len(line_groups) == 0:
            return ""
        
        # Check if this looks like a fraction (numerator over denominator)
        if len(line_groups) == 2:
            top_text = self._extract_spans_text(line_groups[0])
            bottom_text = self._extract_spans_text(line_groups[1])
            
            # If both parts are simple, it might be a fraction
            if len(top_text) < 50 and len(bottom_text) < 50:
                return f"\\frac{{{top_text}}}{{{bottom_text}}}"
        
        # Check if this looks like a square root with content underneath
        first_line_text = self._extract_spans_text(line_groups[0])
        if '√' in first_line_text or '\\sqrt' in first_line_text:
            # Build sqrt with everything below as content
            content_parts = []
            for group in line_groups[1:]:
                content_parts.append(self._extract_spans_text(group))
            
            if len(line_groups) > 2:
                # Likely a fraction inside the sqrt
                numerator = content_parts[0] if len(content_parts) > 0 else ""
                denominator = content_parts[1] if len(content_parts) > 1 else ""
                if numerator and denominator:
                    return f"\\sqrt{{\\frac{{{numerator}}}{{{denominator}}} {' '.join(content_parts[2:])}}}"
            
            content = " ".join(content_parts)
            return f"\\sqrt{{{content}}}"
        
        # Default: concatenate all lines
        all_parts = []
        for group in line_groups:
            all_parts.append(self._extract_spans_text(group))
        return " ".join(all_parts)
    
    def _extract_spans_text(self, spans: List[Dict]) -> str:
        """Extract text from spans with LaTeX formatting."""
        parts = []
        prev_size = None
        
        for span in spans:
            text = span.get("text", "").strip()
            size = span.get("size", 10)
            
            if not text:
                continue
            
            # Convert mathematical symbols
            text = self._convert_math_symbols(text)
            
            # Handle subscripts and superscripts based on size
            if prev_size is not None and size < prev_size * 0.8:
                # This is likely a subscript or superscript
                if '_' not in parts[-1] if parts else True:
                    parts.append(f"_{{{text}}}")
                else:
                    parts.append(text)
            else:
                parts.append(text)
            
            prev_size = size
        
        return " ".join(parts)
    
    def _convert_line_to_latex(self, line: Dict) -> str:
        """Convert a single line to LaTeX."""
        spans = line.get("spans", [])
        return self._extract_spans_text(spans)
    
    def _convert_math_symbols(self, text: str) -> str:
        """Convert Unicode mathematical symbols to LaTeX equivalents."""
        # Common mathematical symbol mappings
        symbol_map = {
            '√': '\\sqrt',
            '∑': '\\sum',
            '∏': '\\prod',
            '∫': '\\int',
            '∂': '\\partial',
            '∆': '\\Delta',
            '∇': '\\nabla',
            '±': '\\pm',
            '≤': '\\leq',
            '≥': '\\geq',
            '≠': '\\neq',
            '≈': '\\approx',
            '∞': '\\infty',
            '×': '\\times',
            '÷': '\\div',
            '∗': '\\ast',
            'α': '\\alpha',
            'β': '\\beta',
            'γ': '\\gamma',
            'δ': '\\delta',
            'ε': '\\epsilon',
            'θ': '\\theta',
            'λ': '\\lambda',
            'μ': '\\mu',
            'π': '\\pi',
            'σ': '\\sigma',
            'τ': '\\tau',
            'φ': '\\phi',
            'ω': '\\omega',
        }
        
        result = text
        for symbol, latex in symbol_map.items():
            result = result.replace(symbol, latex)
        
        return result
