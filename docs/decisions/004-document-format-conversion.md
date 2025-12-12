# ADR-004: Document Format Conversion Strategy

## Status
Accepted

## Date
2025-12-06

## Context

The system must support multiple input document formats used in trading algorithm documentation:
- Microsoft Word (.docx)
- PDF
- reStructuredText (.rst)
- Markdown (.md)

Documents contain sensitive information about quantitative systematic strategies. Maximum document size is 100 pages initially.

AI models work best with structured text that preserves:
- Document hierarchy (headings, sections)
- Code blocks and formulas
- Tables and structured data
- Cross-references and links

## Decision

We will implement a **unified document conversion pipeline** that converts all input formats to **Markdown with metadata** as the canonical AI processing format.

### 1. Conversion Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Input     │────▶│  Converter  │────▶│  Canonical  │
│   Format    │     │   Layer     │     │   Format    │
└─────────────┘     └─────────────┘     └─────────────┘
     │                    │                    │
  .docx, .pdf,      Format-specific      Markdown + 
  .rst, .md         parsers              structured metadata
```

### 2. Canonical Format Structure

```markdown
---
source_format: docx
source_filename: algo_spec_v2.docx
page_count: 45
sections: [...]
extracted_at: 2025-12-06T10:30:00Z
---

# Document Title

## Section 1: Overview
[content with preserved structure]

```python
# Code blocks preserved with language hints
def calculate_signal():
    ...
```

| Table | Preserved |
|-------|-----------|
| as    | markdown  |
```

### 3. Format-Specific Converters

| Format | Library | Notes |
|--------|---------|-------|
| Word (.docx) | python-docx + mammoth | Preserves styles, tables, images |
| PDF | pdfplumber + PyMuPDF | OCR fallback for scanned docs |
| RST | docutils | Native Python support |
| Markdown | Already canonical | Validate and normalize |

### 4. Size Limits

- 100 pages maximum per document
- Estimated ~500 tokens per page average
- ~50,000 tokens maximum per document for AI context

## Consequences

### Positive
- Single format simplifies AI processing
- Markdown is human-readable and version-control friendly
- Preserves document structure for context-aware analysis
- Easy to preview and debug conversions

### Negative
- Some formatting may be lost in conversion
- PDF conversion can be imprecise for complex layouts
- Scanned PDFs require OCR (slower, less accurate)

### Security Considerations
- Conversion happens server-side in isolated environment
- Original files stored encrypted
- Converted text may still contain sensitive content

## Evolution

This ADR has been extended by subsequent decisions:

- **ADR-013**: Enhanced formula handling with LaTeX preservation
- **ADR-014**: Semantic Intermediate Representation for structured entity extraction

The evolution maintains the Markdown output format while adding a semantic layer that captures structured entities (formulas, definitions, tables, cross-references) separately from the rendered Markdown, enabling programmatic validation and AI-optimized processing.

## Related ADRs
- [ADR-003: Multi-Model AI Support](003-multi-model-ai-support.md)
- [ADR-005: Policy Repository System](005-policy-repository-system.md)
- [ADR-013: LaTeX Formula Preservation](013-latex-formula-preservation.md)
- [ADR-014: Semantic Intermediate Representation](014-semantic-intermediate-representation.md)
