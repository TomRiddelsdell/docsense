# ADR-013: LaTeX Formula Preservation in PDF Conversion

## Status
Accepted

## Date
2025-12-09

## Context

When converting PDF documents containing mathematical formulas to Markdown, the original simple text extraction approach resulted in severely degraded formula readability. Mathematical notation in PDFs typically uses:

- Special mathematical fonts (CambriaMath, STIX, Symbol, etc.)
- Unicode mathematical symbols (√, ∑, ∫, etc.)
- Subscripts and superscripts rendered with smaller font sizes
- Complex spatial layouts for fractions, radicals, and multi-line formulas

The original conversion used PyMuPDF's simple `get_text("text")` method, which extracted formulas as plain Unicode text but lost all structural information. For example, the formula for `AssetLongTermVol` was rendered as:

```
𝐴𝑠𝑠𝑒𝑡𝐿𝑜𝑛𝑔𝑇𝑒𝑟𝑚𝑉𝑜𝑙𝑖,𝐼𝑇𝐷= √
216
3 × 𝑁𝐼𝑛𝑖𝑡𝐴𝑠𝑠𝑒𝑡𝑉𝑜𝑙𝐿𝐵
∗ ∑(ln ( 𝐴𝑖,𝑙
𝐴𝑖,𝑙−3
```

This format is virtually unreadable and makes it impossible for users or AI models to understand the mathematical relationships.

### Requirements

1. Preserve mathematical notation during PDF to Markdown conversion
2. Support common mathematical symbols and operators
3. Handle fractions, square roots, and multi-line formulas
4. Ensure formulas render properly in Markdown viewers that support KaTeX/MathJax
5. Maintain readability for AI analysis

## Decision

Implement an enhanced PDF converter that:

1. **Detects mathematical blocks** using font analysis:
   - Identifies mathematical fonts (CambriaMath, STIX, Symbol, MT Extra, etc.)
   - Detects mathematical symbols (√, ∑, ∫, ∏, etc.)
   - Recognizes subscripts/superscripts by font size changes

2. **Converts to LaTeX format**:
   - Uses PyMuPDF's `get_text("dict")` method to extract font and size metadata
   - Converts Unicode mathematical symbols to LaTeX equivalents
   - Detects subscripts/superscripts based on font size (< 80% of previous span)
   - Identifies fractions and square roots by spatial layout
   - Wraps formulas in `$$` blocks for display math

3. **Symbol mappings** include:
   - Greek letters: α→\alpha, β→\beta, λ→\lambda, etc.
   - Operators: √→\sqrt, ∑→\sum, ∫→\int, ×→\times, etc.
   - Comparisons: ≤→\leq, ≥→\geq, ≠→\neq, ≈→\approx

### Implementation

The enhanced `PdfConverter` class:

```python
class PdfConverter(DocumentConverter):
    MATH_FONTS = {
        'CambriaMath', 'STIX', 'MathJax', 'SymbolMT', 'Symbol',
        'MT Extra', 'Cambria-Math', 'Latin Modern Math'
    }
    
    def _is_mathematical_block(self, lines):
        # Detect blocks using math fonts or symbols
        # Returns True if >50% spans use math fonts
        
    def _convert_to_latex(self, lines):
        # Convert PDF spans to LaTeX notation
        # Handle fractions, radicals, subscripts/superscripts
```

### Example Output

The same `AssetLongTermVol` formula now converts to:

```latex
$$
\sqrt{\frac{216}{3 \times 𝑁 _{𝐼𝑛𝑖𝑡𝐴𝑠𝑠𝑒𝑡𝑉𝑜𝑙𝐿𝐵}} }
$$

$$
\ast \sum(ln ( 𝐴 _{𝑖,𝑙}
$$

$$
𝐴 _{𝑖,𝑙−3}
$$

$$
))
$$
```

This renders as proper mathematical notation in Markdown viewers supporting KaTeX/MathJax.

## Consequences

### Positive

- **Preserved readability**: Mathematical formulas remain comprehensible
- **AI-friendly**: AI models can better understand mathematical relationships
- **Standard format**: LaTeX is the de facto standard for mathematical notation
- **Wide support**: KaTeX/MathJax supported by most modern Markdown viewers (GitHub, VS Code, documentation sites)
- **No information loss**: All mathematical structure is preserved

### Negative

- **Complexity**: More complex conversion logic vs simple text extraction
- **Split blocks**: Currently formulas may be split across multiple `$$` blocks due to PDF line structure
- **Processing time**: Font analysis adds ~10-20% to conversion time
- **Fallback needed**: Plain text fallback for viewers without KaTeX support

### Future Improvements

1. **Block consolidation**: Merge consecutive mathematical blocks into single formulas
2. **Advanced layouts**: Better detection of matrices, integrals, and complex expressions
3. **Inline math**: Support for inline formulas using single `$` delimiters
4. **OCR integration**: Handle formulas rendered as images in scanned PDFs

## Related ADRs

- [ADR-004: Document Format Conversion](004-document-format-conversion.md) - Original PDF conversion strategy
- [ADR-009: Document Self-Containment Requirements](009-document-self-containment-requirements.md) - Markdown as canonical format

## References

- [KaTeX Documentation](https://katex.org/docs/supported.html)
- [LaTeX Mathematical Notation](https://en.wikibooks.org/wiki/LaTeX/Mathematics)
- [PyMuPDF Text Extraction](https://pymupdf.readthedocs.io/en/latest/textpage.html)
