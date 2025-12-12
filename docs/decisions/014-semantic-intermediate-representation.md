# ADR-014: Semantic Intermediate Representation for Document Conversion

## Status

Accepted

## Date

2025-12-09

## Context

### Problem Statement

DocSense's current document conversion pipeline transforms input documents (PDF, DOCX, MD, RST) directly to Markdown with basic metadata. This approach has several limitations:

1. **Information Loss**: Mathematical formulas in Word documents (stored as OMML) are completely lost during conversion
2. **No Semantic Structure**: Definitions, terms, cross-references, and formula dependencies are not extracted or tracked
3. **Limited Validation**: All validation relies on AI analysis rather than programmatic checks
4. **Suboptimal LLM Input**: Raw Markdown lacks semantic grouping that would help LLMs reason about document structure

### Current Architecture

```
Input (PDF/DOCX/MD/RST) → Converter → Markdown + Basic Sections → LLM
```

Current `ConversionResult` captures only:
- `markdown_content: str`
- `sections: List[DocumentSection]` (title, content, level)
- `metadata: DocumentMetadata` (title, author, dates, counts)

### Requirements for Trading Algorithm Documentation

Complex systematic trading documents contain:
- **Definitions**: Terms with precise meanings (e.g., "Spread Return means...")
- **Formulas**: Mathematical expressions with variable dependencies
- **Tables**: Parameter schedules, configuration values
- **Cross-references**: Internal references between sections, formulas, tables
- **Domain-specific terminology**: Index components, trading signals, volatility measures

These semantic elements must be preserved for accurate AI analysis and programmatic validation.

## Decision

We will implement a **Semantic Intermediate Representation (IR)** layer between document conversion and AI analysis. This creates a two-layer representation:

1. **Machine-readable structured format (IR)**: JSON-serializable data structures capturing all semantic content
2. **LLM-friendly flattened text**: Structured textual format optimized for AI reasoning

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         NEW CONVERSION PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. INPUT LAYER                                                             │
│     └── PDF, DOCX, Markdown, RST                                            │
│                                                                             │
│  2. EXTRACTION LAYER (Format-Specific Converters)                           │
│     ├── PdfConverter     → Markdown + LaTeX formulas + tables               │
│     ├── WordConverter    → Markdown + OMML→LaTeX formulas + tables          │
│     ├── MarkdownConverter → Pass-through with formula detection             │
│     └── RstConverter     → Markdown with structure preservation             │
│                                                                             │
│  3. SEMANTIC IR LAYER (NEW)                                                 │
│     └── DocumentIR (JSON-serializable)                                      │
│         ├── sections[]     - Hierarchical document structure                │
│         ├── definitions[]  - Term/definition pairs with locations           │
│         ├── formulae[]     - Math expressions with dependencies             │
│         ├── tables[]       - Structured table data                          │
│         ├── cross_refs[]   - Internal reference graph                       │
│         └── metadata       - Document-level information                     │
│                                                                             │
│  4. VALIDATION LAYER (NEW)                                                  │
│     ├── Duplicate definition detection                                      │
│     ├── Undefined variable detection                                        │
│     ├── Circular dependency detection                                       │
│     └── Missing reference detection                                         │
│                                                                             │
│  5. LLM-READY LAYER (NEW)                                                   │
│     └── Flattened semantic text with markers                                │
│         === DEFINITIONS === grouped terms                                   │
│         === FORMULAE === with dependencies                                  │
│         === TABLES === structured summaries                                 │
│         === CONTENT === document sections                                   │
│                                                                             │
│  6. AI ANALYSIS LAYER                                                       │
│     └── LLM receives enriched semantic input + validation pre-results       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Structures

#### DocumentIR (Core Intermediate Representation)

```python
@dataclass
class DocumentIR:
    """Semantic Intermediate Representation for document analysis."""
    document_id: str
    title: str
    original_format: str
    sections: List[IRSection]
    definitions: List[TermDefinition]
    formulae: List[FormulaReference]
    tables: List[TableData]
    cross_references: List[CrossReference]
    metadata: IRMetadata
    raw_markdown: str  # Original markdown for reference
    
    def to_llm_format(self) -> str:
        """Generate LLM-optimized flattened text."""
        
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""
        
    def validate(self) -> List[ValidationIssue]:
        """Run programmatic validation checks."""
```

#### Semantic Entities

```python
@dataclass
class TermDefinition:
    """A defined term within the document."""
    id: str
    term: str
    definition: str
    location: str  # Section reference
    aliases: List[str]
    first_occurrence_line: int

@dataclass
class FormulaReference:
    """A mathematical formula with dependency tracking."""
    id: str
    name: str | None  # e.g., "AssetLongTermVol"
    latex: str
    mathml: str | None
    plain_text: str
    variables: List[str]
    dependencies: List[str]  # Other formula IDs or term IDs
    location: str

@dataclass
class TableData:
    """Structured table representation."""
    id: str
    title: str | None
    headers: List[str]
    rows: List[List[str]]
    column_types: List[str]  # "text", "numeric", "formula"
    location: str

@dataclass
class CrossReference:
    """Internal document reference."""
    source_id: str
    source_type: str  # "section", "formula", "table", "definition"
    target_id: str
    target_type: str
    reference_text: str
```

### Word Document Formula Extraction

Enhance `WordConverter` to extract OMML (Office Math Markup Language):

```python
class WordConverter(DocumentConverter):
    def _extract_omml_formulas(self, doc) -> List[FormulaReference]:
        """Extract equations from Word document."""
        formulas = []
        for para in doc.paragraphs:
            for elem in para._element.iter():
                if elem.tag.endswith('oMath'):
                    omml = etree.tostring(elem, encoding='unicode')
                    latex = self._omml_to_latex(omml)
                    formulas.append(FormulaReference(
                        id=f"formula-{len(formulas)+1}",
                        latex=latex,
                        mathml=self._omml_to_mathml(omml),
                        plain_text=self._omml_to_text(omml),
                        ...
                    ))
        return formulas
```

### Definition Extraction

Pattern-based extraction for common definition formats:

```python
class DefinitionExtractor:
    PATTERNS = [
        # "Term" means definition
        r'"([^"]+)"\s+means\s+(.+?)(?=\n\n|$)',
        # "Term" refers to definition
        r'"([^"]+)"\s+(?:refers to|shall mean|is defined as)\s+(.+?)(?=\n\n|$)',
        # Term: definition (glossary style)
        r'^([A-Z][a-zA-Z\s]+):\s*(.+?)(?=\n\n|$)',
        # Term – definition (dash style)
        r'^([A-Z][a-zA-Z\s]+)\s*[–-]\s*(.+?)(?=\n\n|$)',
    ]
```

### LLM-Ready Output Format

```text
=== DOCUMENT METADATA ===
Title: GSEMA8 Index Methodology
Format: PDF
Pages: 39
Extracted: 2025-12-09T10:30:00Z

=== DEFINITIONS (15 terms) ===
TERM: Asset Realized Long-Term Volatility
Definition: The two-year realized volatility of each Index Component
Location: Section 8.5
Aliases: AssetLongTermVol

TERM: Base Index Asset Weight
Definition: The weight assigned to each Index Component after applying Risk Budget allocation
Location: Section 8.1
Used by: Formula_3, Formula_7

=== FORMULAE (12 formulas) ===
FORMULA: AssetLongTermVol (Formula_5)
LaTeX: \sqrt{\frac{216}{3 \times N_{InitAssetVolLB}} \ast \sum(ln(\frac{A_{i,l}}{A_{i,l-3}}))^2}
Variables: N_InitAssetVolLB, A_i_l, A_i_l-3
Depends on: InitAssetVolLB (defined in Annex A)
Location: Section 8.5

=== TABLES (8 tables) ===
TABLE: Parameter Schedule (Table 1)
Columns: Parameter | Value | Description
Row count: 12
Location: Section 5.2

=== VALIDATION ISSUES (pre-computed) ===
⚠️ UNDEFINED_VARIABLE: Variable "Lambda" in Formula_7 is not defined
⚠️ MISSING_REFERENCE: Section 8.3 references "Annex B" which does not exist

=== DOCUMENT CONTENT ===
## Section 1: Overview
[content...]

## Section 2: Index Components
[content...]
```

## Consequences

### Positive

- **Complete semantic preservation**: All definitions, formulas, tables, and references captured
- **Programmatic validation**: Detect issues before AI analysis (faster, cheaper, deterministic)
- **Better AI analysis**: LLMs receive structured, enriched input with pre-computed context
- **Multi-format formulas**: Store LaTeX, MathML, and plain-text representations
- **Dependency tracking**: Formula dependencies enable circular reference detection
- **Audit-ready**: IR provides traceable, reproducible extraction

### Negative

- **Increased complexity**: More code to maintain in extraction pipeline
- **Processing overhead**: IR generation adds ~10-20% to conversion time
- **Pattern limitations**: Definition extraction may miss non-standard formats
- **OMML complexity**: Word formula conversion requires additional dependencies

### Neutral

- **Backward compatible**: Existing `markdown_content` field preserved in events
- **Optional adoption**: IR can be generated on-demand, not required for all documents
- **Iterative improvement**: Extraction patterns can be refined over time

## Alternatives Considered

### Alternative 1: Enhanced Markdown with Frontmatter

Store semantic data in YAML frontmatter within Markdown.

**Why rejected**: 
- Mixing structure with content complicates parsing
- Frontmatter becomes unwieldy for many definitions/formulas
- Difficult to represent complex relationships (dependencies, cross-refs)

### Alternative 2: HTML + MathML as Canonical Format

Convert all documents to HTML with embedded MathML.

**Why rejected**:
- HTML is verbose and less LLM-friendly than structured text
- MathML is harder for LLMs to reason about than LaTeX
- Adds unnecessary complexity for non-math content

### Alternative 3: Direct AI Extraction

Let the AI extract definitions, formulas, and validate during analysis.

**Why rejected**:
- Expensive (LLM tokens for extraction + analysis)
- Non-deterministic extraction results
- No pre-validation before costly AI calls
- Harder to debug and audit

## Implementation Plan

See `/docs/IMPLEMENTATION_PLAN.md` Phase 10: Semantic IR Implementation.

## References

- [ADR-004: Document Format Conversion](004-document-format-conversion.md)
- [ADR-013: LaTeX Formula Preservation](013-latex-formula-preservation.md)
- [Analysis: Document Conversion Improvement Recommendations](/docs/analysis/document-conversion-improvement-recommendations.md)
- [OMML Specification](https://docs.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/)
- [MathML Specification](https://www.w3.org/Math/)

