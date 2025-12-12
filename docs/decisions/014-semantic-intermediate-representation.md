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
│     ├── Missing reference detection                                         │
│     ├── Dependency graph construction                                       │
│     ├── Lineage computation (forward/backward tracking)                     │
│     └── Impact analysis (change propagation)                                │
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

    # DEPENDENCY GRAPH AND LINEAGE
    dependency_graph: DependencyGraph  # Complete dependency graph
    lineage_cache: Dict[str, Lineage]  # Pre-computed lineage for all entities

    def to_llm_format(self) -> str:
        """Generate LLM-optimized flattened text with dependency info."""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dictionary."""

    def validate(self) -> List[ValidationIssue]:
        """Run programmatic validation checks including dependency analysis."""

    def get_impact_analysis(self, entity_id: str) -> ImpactAnalysis:
        """Compute impact of changing an entity."""

    def get_entity_lineage(self, entity_id: str) -> Lineage:
        """Get complete lineage for an entity."""

@dataclass
class DependencyGraph:
    """Directed acyclic graph of entity dependencies."""
    edges: List[DependencyEdge]
    nodes: Dict[str, GraphNode]  # entity_id -> node

    def add_edge(self, source_id: str, target_id: str, **metadata) -> None:
        """Add dependency edge from source to target."""

    def get_parents(self, entity_id: str) -> List[str]:
        """Get direct dependencies (what this entity depends on)."""

    def get_children(self, entity_id: str) -> List[str]:
        """Get direct dependents (what depends on this entity)."""

    def get_ancestors(self, entity_id: str) -> List[str]:
        """Get all transitive dependencies."""

    def get_descendants(self, entity_id: str) -> List[str]:
        """Get all transitive dependents."""

    def detect_cycles(self) -> List[List[str]]:
        """Detect circular dependencies."""

    def compute_depth(self, entity_id: str) -> int:
        """Compute dependency depth (0 = no dependencies)."""

    def topological_sort(self) -> List[str]:
        """Return entities in dependency order."""

@dataclass
class DependencyEdge:
    """An edge in the dependency graph."""
    source_id: str  # Provider of input/parameter
    target_id: str  # Consumer of input/parameter
    edge_type: str  # "provides_variable", "provides_parameter", "references"
    metadata: Dict[str, Any]  # Variable name, parameter name, etc.

@dataclass
class GraphNode:
    """A node in the dependency graph."""
    entity_id: str
    entity_type: str  # "term", "formula", "table"
    name: str
    in_degree: int  # Number of dependencies
    out_degree: int  # Number of dependents
```

#### Semantic Entities

```python
@dataclass
class TermDefinition:
    """A defined term within the document with dependency tracking."""
    id: str
    term: str
    definition: str
    location: str  # Section reference
    aliases: List[str]
    first_occurrence_line: int

    # LINEAGE TRACKING
    depends_on: List[str]  # IDs of other terms/formulas referenced in definition
    used_by: List[str]  # IDs of formulas/terms that reference this term
    inputs: List[TermInput]  # Input parameters used in this definition

@dataclass
class TermInput:
    """Input parameter or reference within a term definition."""
    name: str  # The input/parameter name
    source_id: str | None  # ID of the source entity (formula, table, term)
    source_type: str | None  # "formula", "table", "term", "external"
    description: str | None  # Description of the input

@dataclass
class FormulaReference:
    """A mathematical formula with comprehensive dependency tracking."""
    id: str
    name: str | None  # e.g., "AssetLongTermVol"
    latex: str
    mathml: str | None
    plain_text: str
    location: str

    # LINEAGE TRACKING
    variables: List[FormulaVariable]  # All variables with their sources
    parameters: List[FormulaParameter]  # Constants/parameters with their sources
    depends_on: List[str]  # IDs of formulas/terms/tables this formula depends on
    used_by: List[str]  # IDs of formulas that use this formula's result

@dataclass
class FormulaVariable:
    """A variable within a formula with source tracking."""
    name: str  # Variable name (e.g., "N_InitAssetVolLB")
    source_id: str | None  # ID of source (term, table, formula)
    source_type: str | None  # "term", "table", "formula", "undefined"
    description: str | None  # Description from source
    is_derived: bool  # True if computed from another formula

@dataclass
class FormulaParameter:
    """A parameter/constant within a formula."""
    name: str  # Parameter name
    value: str | None  # Value if specified
    source_id: str | None  # ID of table/term defining this parameter
    source_type: str | None  # "table", "term", "inline"
    description: str | None

@dataclass
class TableData:
    """Structured table representation with parameter tracking."""
    id: str
    title: str | None
    headers: List[str]
    rows: List[List[str]]
    column_types: List[str]  # "text", "numeric", "formula"
    location: str

    # LINEAGE TRACKING
    provides_parameters: List[TableParameter]  # Parameters defined in this table
    used_by: List[str]  # IDs of formulas/terms using this table's data

@dataclass
class TableParameter:
    """A parameter defined in a table."""
    name: str  # Parameter name (from table cell)
    value: str  # Parameter value
    row_index: int
    column_name: str  # Header name
    description: str | None  # From description column if present

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

### Dependency Graph and Lineage Tracking

The IR maintains a complete dependency graph enabling:

1. **Forward tracking**: What formulas/terms use this entity?
2. **Backward tracking**: What inputs does this entity depend on?
3. **Impact analysis**: If a parameter changes, what is affected?
4. **Validation**: Detect circular dependencies, undefined references

#### Dependency Graph Builder

```python
class DependencyGraphBuilder:
    """Build dependency graph from semantic entities."""

    def build_graph(self, document_ir: DocumentIR) -> DependencyGraph:
        """Construct complete dependency graph."""
        graph = DependencyGraph()

        # Index all entities
        entities = {}
        for term in document_ir.definitions:
            entities[term.id] = ("term", term)
        for formula in document_ir.formulae:
            entities[formula.id] = ("formula", formula)
        for table in document_ir.tables:
            entities[table.id] = ("table", table)

        # Build forward and backward links
        for formula in document_ir.formulae:
            # Link variables to their sources
            for var in formula.variables:
                if var.source_id:
                    graph.add_edge(var.source_id, formula.id,
                                   edge_type="provides_variable",
                                   variable_name=var.name)

            # Link parameters to their sources
            for param in formula.parameters:
                if param.source_id:
                    graph.add_edge(param.source_id, formula.id,
                                   edge_type="provides_parameter",
                                   parameter_name=param.name)

        return graph

    def compute_lineage(self, entity_id: str, graph: DependencyGraph) -> Lineage:
        """Compute complete lineage for an entity."""
        return Lineage(
            entity_id=entity_id,
            direct_dependencies=graph.get_parents(entity_id),
            transitive_dependencies=graph.get_ancestors(entity_id),
            direct_dependents=graph.get_children(entity_id),
            transitive_dependents=graph.get_descendants(entity_id),
            dependency_depth=graph.compute_depth(entity_id),
        )

@dataclass
class Lineage:
    """Complete lineage information for an entity."""
    entity_id: str
    direct_dependencies: List[str]  # Immediate parents
    transitive_dependencies: List[str]  # All ancestors
    direct_dependents: List[str]  # Immediate children
    transitive_dependents: List[str]  # All descendants
    dependency_depth: int  # Depth in dependency tree (0 = no dependencies)
```

#### Example Dependency Chain

```
Table_1 (Parameter Schedule)
  └─ provides parameter "Lambda" (value: 0.85)
       └─ used by Formula_3 (Risk Budget Allocation)
            └─ provides variable "RiskBudgetWeight"
                 └─ used by Formula_7 (Final Asset Weight)
                      └─ provides variable "FinalWeight"
                           └─ used by Term_5 (Target Portfolio Weights)

Lineage for Formula_7:
  Direct dependencies: [Formula_3, Table_2]
  Transitive dependencies: [Formula_3, Table_1, Table_2, Term_2]
  Direct dependents: [Term_5, Formula_9]
  Transitive dependents: [Term_5, Formula_9, Formula_10]
  Dependency depth: 2
```

#### JSON Serialization Example

Example of how a formula with full lineage tracking is serialized:

```json
{
  "id": "Formula_7",
  "name": "Final Asset Weight",
  "latex": "W_{i,t} = \\frac{RBW_{i,t} \\times TargetVol}{\\sigma_{i,t}}",
  "mathml": null,
  "plain_text": "W_i_t = (RBW_i_t * TargetVol) / sigma_i_t",
  "location": "Section 8.3",

  "variables": [
    {
      "name": "RBW_i_t",
      "source_id": "Formula_3",
      "source_type": "formula",
      "description": "Risk Budget Weight from risk allocation formula",
      "is_derived": true
    },
    {
      "name": "TargetVol",
      "source_id": "Table_1",
      "source_type": "table",
      "description": "Target annual volatility (from row 1)",
      "is_derived": false
    },
    {
      "name": "sigma_i_t",
      "source_id": "Formula_5",
      "source_type": "formula",
      "description": "Asset realized long-term volatility",
      "is_derived": true
    }
  ],

  "parameters": [],

  "depends_on": ["Formula_3", "Formula_5", "Table_1"],
  "used_by": ["Formula_9", "Term_5"],

  "lineage": {
    "entity_id": "Formula_7",
    "direct_dependencies": ["Formula_3", "Formula_5", "Table_1"],
    "transitive_dependencies": ["Formula_2", "Formula_3", "Formula_5", "Table_1", "Table_2", "Term_1"],
    "direct_dependents": ["Formula_9", "Term_5"],
    "transitive_dependents": ["Formula_9", "Formula_10", "Term_5", "Term_6"],
    "dependency_depth": 3
  }
}
```

### LLM-Ready Output Format

```text
=== DOCUMENT METADATA ===
Title: GSEMA8 Index Methodology
Format: PDF
Pages: 39
Extracted: 2025-12-09T10:30:00Z

=== DEFINITIONS (15 terms) ===
TERM: Asset Realized Long-Term Volatility [Term_8]
Definition: The two-year realized volatility of each Index Component
Location: Section 8.5
Aliases: AssetLongTermVol
Inputs:
  - Index Component (source: Term_1, type: term)
  - Two-year period (source: Table_3, type: table, parameter)
Used by: Formula_5, Formula_12
Dependency depth: 1

TERM: Base Index Asset Weight [Term_3]
Definition: The weight assigned to each Index Component after applying Risk Budget allocation
Location: Section 8.1
Depends on:
  - Risk Budget allocation (Formula_3)
  - Index Component weight (Table_1)
Used by: Formula_7, Formula_9
Dependency depth: 2

=== FORMULAE (12 formulas) ===
FORMULA: AssetLongTermVol [Formula_5]
LaTeX: \sqrt{\frac{216}{3 \times N_{InitAssetVolLB}} \ast \sum(ln(\frac{A_{i,l}}{A_{i,l-3}}))^2}
Location: Section 8.5

Variables:
  - N_InitAssetVolLB (source: Table_1, type: table, row 3)
  - A_i_l (source: Formula_2, type: formula, derived)
  - A_i_l-3 (source: Formula_2, type: formula, derived)

Parameters:
  - 216 (inline constant, number of periods)
  - 3 (inline constant, lookback spacing)

Dependencies:
  - Direct: Formula_2 (Asset Price), Table_1 (Parameters)
  - Transitive: Term_1 (Index Component), Table_2 (Asset Universe)

Used by: Formula_7 (Final Weight Calculation), Term_8 (Asset Volatility)
Dependency depth: 2

FORMULA: Final Asset Weight [Formula_7]
LaTeX: W_{i,t} = \frac{RBW_{i,t} \times TargetVol}{\sigma_{i,t}}
Location: Section 8.3

Variables:
  - RBW_i_t (source: Formula_3, type: formula, description: "Risk Budget Weight")
  - TargetVol (source: Table_1, type: table, row 1, value: 0.10)
  - sigma_i_t (source: Formula_5, type: formula, description: "Asset Volatility")

Parameters:
  - None (all inputs are variables)

Dependencies:
  - Direct: Formula_3, Formula_5, Table_1
  - Transitive: Formula_2, Table_2, Term_1, Term_8

Used by: Formula_9 (Portfolio Construction), Term_5 (Final Weights)
Dependency depth: 3

=== TABLES (8 tables) ===
TABLE: Parameter Schedule [Table_1]
Columns: Parameter | Value | Description
Row count: 12
Location: Section 5.2

Provides parameters:
  - TargetVol: 0.10 (row 1, used by: Formula_7, Formula_9)
  - Lambda: 0.85 (row 2, used by: Formula_3)
  - N_InitAssetVolLB: 520 (row 3, used by: Formula_5)
  - MaxWeight: 0.25 (row 5, used by: Formula_8)

Used by: Formula_3, Formula_5, Formula_7, Formula_8, Formula_9

=== DEPENDENCY GRAPH (summary) ===
Root entities (no dependencies): Table_1, Table_2, Term_1
Leaf entities (not used by others): Formula_10, Term_12
Max dependency depth: 4
Circular dependencies: None detected

Critical paths:
  Table_1 → Formula_3 → Formula_7 → Formula_9 → Formula_10 (depth: 4)
  Table_2 → Formula_2 → Formula_5 → Formula_7 → Formula_9 (depth: 4)

=== VALIDATION ISSUES (pre-computed) ===
✓ All variables resolved
✓ No circular dependencies
✓ All table parameters referenced
⚠️ ORPHANED_TERM: Term_12 defined but never referenced
⚠️ MISSING_SOURCE: Formula_6 references parameter "Kappa" not found in tables or terms

=== IMPACT ANALYSIS ===
If Table_1 parameter "Lambda" changes:
  Directly affected: Formula_3
  Transitively affected: Formula_7, Formula_9, Formula_10, Term_5, Term_6
  Total downstream impact: 6 entities

=== DOCUMENT CONTENT ===
## Section 1: Overview
[content...]

## Section 2: Index Components
[content...]
```

## Use Cases for Dependency Tracking and Lineage

### 1. Impact Analysis

**Scenario**: A parameter in Table_1 changes from 0.85 to 0.90

**Query**: "What formulas and terms are affected?"

**Response**:

```text
Parameter: Lambda (Table_1, row 2)
Current value: 0.85 → New value: 0.90

Direct impact:
  - Formula_3 (Risk Budget Allocation) - uses Lambda directly

Transitive impact:
  - Formula_7 (Final Asset Weight) - depends on Formula_3
  - Formula_9 (Portfolio Construction) - depends on Formula_7
  - Formula_10 (Rebalancing Logic) - depends on Formula_9
  - Term_5 (Target Portfolio Weights) - references Formula_7
  - Term_6 (Portfolio Constraints) - references Term_5

Total entities affected: 6
Max propagation depth: 4
```

### 2. Variable Source Tracking

**Scenario**: Formula uses variable "TargetVol"

**Query**: "Where does TargetVol come from?"

**Response**:

```text
Variable: TargetVol
Used in: Formula_7, Formula_9

Source: Table_1 (Parameter Schedule)
  Row: 1
  Value: 0.10
  Description: "Target annual volatility for the index"
  Column: Value

Lineage:
  Table_1 (row 1) → TargetVol → Formula_7 → Formula_9
```

### 3. Missing Definition Detection

**Scenario**: Formula references undefined variable

**Query**: "Are all variables defined?"

**Response**:

```text
Formula_6: Portfolio Risk Calculation
Variables:
  ✓ sigma_i (source: Formula_5, AssetLongTermVol)
  ✓ w_i (source: Formula_7, Final Asset Weight)
  ✗ Kappa (source: UNDEFINED)

Error: Variable "Kappa" is not defined in any table or term.
Suggestion: Check if "Kappa" should be defined in Parameter Schedule (Table_1)
```

### 4. Circular Dependency Detection

**Scenario**: Formula A depends on Formula B which depends on Formula A

**Query**: "Are there any circular dependencies?"

**Response**:

```text
Circular dependency detected:

Formula_12 (Asset Correlation)
  → depends on Formula_15 (Covariance Matrix)
    → depends on Formula_12 (Asset Correlation)

Dependency chain:
  Formula_12 → Formula_15 → Formula_12

This creates an infinite loop and must be resolved.
```

### 5. Documentation Completeness Check

**Scenario**: Check if all defined terms are actually used

**Query**: "Are there any orphaned definitions?"

**Response**:

```text
Orphaned terms (defined but never referenced):
  - Term_12: "Adjustment Factor"
    Location: Section 9.2
    Defined but not used by any formula or other term

  - Term_18: "Legacy Weight Calculation"
    Location: Annex C
    May be deprecated documentation

Suggestion: Either remove unused terms or verify they should be referenced.
```

### 6. Change Validation

**Scenario**: Before modifying a formula, understand its impact

**Query**: "What uses Formula_5 (AssetLongTermVol)?"

**Response**:

```text
Formula_5 (AssetLongTermVol) is used by:

Direct dependents:
  - Formula_7 (Final Asset Weight)
    Variable: sigma_i_t
  - Formula_11 (Risk Contribution)
    Variable: vol_i
  - Term_8 (Asset Realized Long-Term Volatility)
    Referenced in definition

Transitive dependents (will be indirectly affected):
  - Formula_9 (Portfolio Construction)
  - Formula_10 (Rebalancing Logic)
  - Term_5 (Target Portfolio Weights)
  - Term_14 (Risk Budget Allocation)

Total downstream impact: 7 entities

Warning: Modifying this formula affects critical portfolio construction logic.
Recommend comprehensive testing after changes.
```

## Consequences

### Positive

- **Complete semantic preservation**: All definitions, formulas, tables, and references captured
- **Comprehensive dependency tracking**: Full lineage for every term, formula, and parameter
  - Track inputs and sources for each entity
  - Build complete dependency graphs
  - Compute forward/backward lineage
  - Enable impact analysis (what changes if a parameter is modified?)
- **Programmatic validation**: Detect issues before AI analysis (faster, cheaper, deterministic)
  - Undefined variables
  - Circular dependencies
  - Orphaned terms
  - Missing parameter sources
- **Better AI analysis**: LLMs receive structured, enriched input with pre-computed context
  - Dependency information in LLM prompt
  - Pre-computed validation results
  - Impact analysis summary
- **Multi-format formulas**: Store LaTeX, MathML, and plain-text representations
- **Parameter lineage**: Track every parameter from source (table/term) to usage (formula)
- **Change impact analysis**: Identify all downstream effects of parameter changes
- **Audit-ready**: IR provides traceable, reproducible extraction with full provenance

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
