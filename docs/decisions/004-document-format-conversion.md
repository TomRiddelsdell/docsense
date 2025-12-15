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

### AI-Driven Semantic Curation

The conversion pipeline now includes an **AI-driven curation step** to finalize the semantic representation after pattern-based extraction:

```text
┌─────────────────────────────────────────────────────────────────────┐
│                   COMPLETE CONVERSION PIPELINE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. FORMAT-SPECIFIC EXTRACTION                                      │
│     └── Pattern-based parsing (OMML, LaTeX, tables, definitions)   │
│                                                                     │
│  2. INITIAL SEMANTIC IR CONSTRUCTION                                │
│     └── Build DocumentIR with extracted entities                   │
│                                                                     │
│  3. AI-DRIVEN CURATION (NEW)                                        │
│     ├── Dependency resolution and inference                         │
│     │   • Match variables to source definitions                     │
│     │   • Infer implicit dependencies                               │
│     │   • Resolve naming ambiguities                                │
│     │                                                                │
│     ├── Relationship validation                                     │
│     │   • Verify formula-parameter connections                      │
│     │   • Validate cross-reference targets                          │
│     │   • Disambiguate similar term names                           │
│     │                                                                │
│     ├── Missing entity detection                                    │
│     │   • Identify undefined variables in formulas                  │
│     │   • Detect implicit definitions in prose                      │
│     │   • Suggest missing table parameters                          │
│     │                                                                │
│     └── Semantic enrichment                                         │
│         • Add inferred descriptions for variables                   │
│         • Classify formula types (signal, risk, weight)             │
│         • Extract implicit relationships from narrative text        │
│                                                                     │
│  4. FINAL VALIDATED IR                                              │
│     └── Complete DocumentIR with curated dependencies               │
│                                                                     │
│  5. LLM-READY OUTPUT GENERATION                                     │
│     └── Flattened semantic text with dependency information         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

#### Why AI Curation is Required

Pattern-based extraction (Step 1-2) handles explicit, well-formatted semantic content but cannot:

1. **Resolve ambiguous references**: A formula uses variable "Vol" - does it refer to "Target Volatility" (Table_1), "Asset Volatility" (Formula_5), or "Index Volatility" (Term_3)?

2. **Infer implicit dependencies**: A term definition states "calculated using the risk allocation methodology" - which specific formula(s) does this reference?

3. **Match variations**: Parameter "λ" in a formula vs "Lambda" in a table vs "lambda (decay factor)" in text - AI recognizes these as the same entity.

4. **Extract definitions from prose**: "The lookback period is 520 business days" appears in a paragraph, not a formal "X means Y" definition.

5. **Understand domain semantics**: Distinguish between "return" (financial gain) vs "return" (function output) vs "spread return" (specific strategy component).

#### AI Curation Process

The AI model (typically Claude or GPT-4) receives:

**Input**:

- Initial DocumentIR with pattern-extracted entities
- Original Markdown content for context
- Domain-specific glossary and conventions

**Tasks**:

1. For each formula variable without a source: search definitions, tables, and other formulas to identify the likely source
2. For each undefined variable: determine if it's truly missing or just named differently
3. For each term: identify other entities that implicitly reference it
4. For parameter names: normalize variations (Greek letters, abbreviations, case differences)
5. For cross-references: resolve textual references to specific entity IDs

**Output**:

- Enriched DocumentIR with:
  - `source_id` populated for previously unlinked variables
  - `inferred: true` flag for AI-determined relationships
  - `confidence: float` score for each inference
  - `description` fields populated from context
  - Complete dependency graph with both explicit and inferred edges

#### Example: AI Curation in Action

**Before AI Curation**:

```json
{
  "id": "Formula_7",
  "variables": [
    {
      "name": "RBW",
      "source_id": null,  // Pattern extraction couldn't find source
      "source_type": "undefined"
    },
    {
      "name": "σ_i",
      "source_id": null,  // Greek letter notation not matched
      "source_type": "undefined"
    }
  ]
}
```

**After AI Curation**:

```json
{
  "id": "Formula_7",
  "variables": [
    {
      "name": "RBW",
      "source_id": "Formula_3",
      "source_type": "formula",
      "description": "Risk Budget Weight from risk allocation",
      "inferred": true,
      "confidence": 0.95,
      "inference_reason": "Matched to 'RiskBudgetWeight' in Formula_3 (common abbreviation)"
    },
    {
      "name": "σ_i",
      "source_id": "Formula_5",
      "source_type": "formula",
      "description": "Asset long-term volatility",
      "inferred": true,
      "confidence": 0.92,
      "inference_reason": "Greek sigma commonly represents volatility; matched to 'AssetLongTermVol' output"
    }
  ]
}
```

#### Curation Quality Assurance

- **Confidence thresholds**: Only accept inferences with confidence > 0.80
- **Human review flagging**: Inferences with 0.80-0.90 confidence flagged for review
- **Audit trail**: All AI-made decisions recorded in IR metadata
- **Validation feedback loop**: User corrections used to improve future curation

#### Performance Considerations

- **Cost**: AI curation adds ~2-5 cents per document (depending on size and complexity)
- **Time**: +10-30 seconds per document for AI inference
- **Accuracy**: 90-95% precision for dependency inference (vs. ~60-70% for pure pattern matching)

This AI-driven curation step is **essential** for achieving production-quality semantic representations of complex trading algorithm documentation, where implicit relationships and naming variations are common.

## Related ADRs

- [ADR-003: Multi-Model AI Support](003-multi-model-ai-support.md)
- [ADR-005: Policy Repository System](005-policy-repository-system.md)
- [ADR-013: LaTeX Formula Preservation](013-latex-formula-preservation.md)
- [ADR-014: Semantic Intermediate Representation](014-semantic-intermediate-representation.md)
