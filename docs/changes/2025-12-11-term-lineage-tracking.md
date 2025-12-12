# Term Lineage Tracking Implementation

**Date**: 2025-12-11
**Author**: Claude Code
**Status**: ✅ Complete

## Summary

Implemented comprehensive term lineage tracking for the Semantic IR system. Every defined term now captures its input dependencies, parameters, and computational relationships in a machine-parsable data structure. This enables dependency graph analysis and impact assessment.

## Changes Made

### New Files Created

1. **`/workspaces/src/domain/value_objects/semantic_ir/term_lineage.py`** [NEW]
   - `DependencyType` enum: Types of term dependencies
   - `TermDependency` dataclass: Represents dependency on another term
   - `Parameter` dataclass: Represents parameters with type, units, constraints
   - `TermLineage` dataclass: Complete lineage information structure
   - All classes include `to_dict()` and `from_dict()` for serialization

2. **`/workspaces/src/infrastructure/semantic/lineage_extractor.py`** [NEW]
   - `LineageExtractor` class: Pattern-based lineage extraction
   - Extracts term dependencies, parameters, formulas, computations
   - Supports percentages, numeric values with units, variables
   - Identifies conditional dependencies

3. **`/workspaces/test_lineage.py`** [NEW]
   - Comprehensive test script for lineage extraction
   - Tests serialization and deserialization
   - Validates round-trip integrity

### Modified Files

1. **`/workspaces/src/domain/value_objects/semantic_ir/term_definition.py`**
   - Added `lineage: Optional[TermLineage] = None` field
   - Added `to_dict()` method for custom serialization
   - Added `from_dict()` class method for deserialization
   - Properly handles nested TermLineage serialization

2. **`/workspaces/src/domain/value_objects/semantic_ir/__init__.py`**
   - Exported new types: `TermLineage`, `TermDependency`, `Parameter`, `DependencyType`

3. **`/workspaces/src/domain/value_objects/semantic_ir/document_ir.py`**
   - Updated `to_dict()` to use `TermDefinition.to_dict()` instead of `asdict()`
   - Ensures lineage is properly serialized in DocumentIR

4. **`/workspaces/src/infrastructure/semantic/definition_extractor.py`**
   - Added `LineageExtractor` initialization
   - Implemented two-pass extraction:
     - First pass: Extract all term definitions
     - Second pass: Extract lineage with full term knowledge
   - Each `TermDefinition` now includes complete lineage

5. **`/workspaces/src/infrastructure/semantic/ai_curator.py`**
   - Added lineage imports and `LineageExtractor` instance
   - Updated `_find_missed_definitions()` to extract lineage for AI-discovered terms
   - Maintains lineage consistency between rule-based and AI extraction

## Technical Details

### TermLineage Data Structure

```python
@dataclass(frozen=True)
class TermLineage:
    """Complete lineage information for a term."""
    input_terms: List[TermDependency] = field(default_factory=list)
    parameters: List[Parameter] = field(default_factory=list)
    is_computed: bool = False
    computation_description: str = ""
    formula: Optional[str] = None
    conditions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Dependency Types

- `DIRECT_REFERENCE`: Term directly references another defined term
- `PARAMETER`: Term uses a parameter/variable
- `FORMULA_INPUT`: Term is an input to a formula
- `COMPUTED_FROM`: Term is computed from other terms
- `CONDITIONAL_ON`: Term depends conditionally on another

### Parameter Tracking

Parameters include:
- **Type**: numeric, date, percentage, text, duration, currency, basis_points
- **Units**: USD, days, percent, etc.
- **Default values**: Extracted from definitions
- **Context**: Surrounding text for reference

### Two-Pass Extraction Strategy

The extractor uses a two-pass approach to handle forward references:

1. **First Pass**: Extract all term names and definitions
2. **Second Pass**: Extract lineage with knowledge of all available terms

This ensures terms can reference other terms defined later in the document.

## Test Results

Successfully tested with sample trading algorithm documentation:

- ✅ Extracted 5 definitions with complete lineage
- ✅ Identified term dependencies: "Risk-Adjusted Return" → "Volatility"
- ✅ Extracted parameters: "30 days", "2.5%"
- ✅ Identified computed terms (division, sum, subtraction)
- ✅ Serialization to JSON-compatible dict
- ✅ Deserialization from dict (round-trip integrity)

### Example Output

```
Term: Sharpe Ratio
Lineage Information:
  - Is Computed: True
  - Input Terms (1):
    • Risk-Adjusted Return (direct_reference)
  - Parameters (1):
    • 2.5% (percentage)
      Units: percent
      Default: 2.5
  - Computation: "Risk-Adjusted Return" minus the risk-free rate...
  - Conditions: 1
```

## Use Cases Enabled

1. **Dependency Graph Visualization**: Build graph of term relationships
2. **Impact Analysis**: Identify which terms are affected by changes
3. **Validation**: Detect circular dependencies and missing references
4. **Documentation Quality**: Ensure terms are self-contained
5. **AI Analysis**: Provide structured context for semantic analysis
6. **Search & Navigation**: Navigate from term to dependencies

## Related ADRs

- [ADR-001: DDD with Event Sourcing and CQRS](../decisions/001-use-ddd-event-sourcing-cqrs.md)
- [ADR-009: Document Self-Containment Requirements](../decisions/009-document-self-containment-requirements.md)

## Next Steps

Potential enhancements:
- Visualize dependency graphs in frontend UI
- Add cycle detection for circular dependencies
- Implement "find all usages" for terms
- Add lineage-based validation rules
- Export lineage to graph databases (Neo4j)

## Rationale

Term lineage tracking is essential for:

1. **Document Quality Analysis**: Identify undefined references and orphaned terms
2. **Semantic Understanding**: Understand computation flows and data dependencies
3. **Impact Assessment**: Know which terms are affected by policy changes
4. **Self-Containment Validation**: Verify all referenced terms are defined
5. **Machine-Parsable Storage**: Enable automated analysis and processing

The implementation uses pattern-based extraction augmented with AI discovery, ensuring comprehensive coverage of both common and non-standard definition formats.

## Testing Checklist

- [x] Create lineage data structure
- [x] Implement lineage extractor
- [x] Update TermDefinition with lineage field
- [x] Add serialization/deserialization methods
- [x] Integrate with rule-based extractor
- [x] Integrate with AI curator
- [x] Test two-pass extraction
- [x] Test serialization round-trip
- [x] Verify parameter extraction
- [x] Verify term dependency extraction
- [x] Verify computation detection

## Files Added/Modified

**Added** (3 files):
- `/workspaces/src/domain/value_objects/semantic_ir/term_lineage.py`
- `/workspaces/src/infrastructure/semantic/lineage_extractor.py`
- `/workspaces/test_lineage.py`

**Modified** (5 files):
- `/workspaces/src/domain/value_objects/semantic_ir/term_definition.py`
- `/workspaces/src/domain/value_objects/semantic_ir/__init__.py`
- `/workspaces/src/domain/value_objects/semantic_ir/document_ir.py`
- `/workspaces/src/infrastructure/semantic/definition_extractor.py`
- `/workspaces/src/infrastructure/semantic/ai_curator.py`

---

**Status**: ✅ All tasks completed successfully
