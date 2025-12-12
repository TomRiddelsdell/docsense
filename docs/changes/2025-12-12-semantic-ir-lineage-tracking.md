# Semantic IR: Enhanced Dependency Tracking and Lineage

**Date**: 2025-12-12
**Author**: Claude Code
**Type**: Enhancement
**Related ADR**: [ADR-014: Semantic Intermediate Representation](../decisions/014-semantic-intermediate-representation.md)
**Status**: Completed

## Summary

Enhanced the Semantic Intermediate Representation (IR) ADR to include comprehensive dependency tracking and lineage capabilities for all semantic entities (terms, formulas, tables). Each entity now tracks its inputs, parameters, dependencies, and usage, enabling complete lineage analysis and impact assessment.

## Motivation

The original ADR-014 introduced semantic extraction but didn't fully specify how to track the relationships between entities. For a robust document analysis system, we need:

1. **Complete lineage tracking**: Know exactly where each input/parameter comes from
2. **Dependency graphs**: Build a complete graph of all entity relationships
3. **Impact analysis**: Understand what changes if a parameter is modified
4. **Validation enhancement**: Detect undefined variables, circular dependencies, orphaned terms
5. **Better AI analysis**: Provide LLMs with pre-computed dependency information

## Changes

### Updated Data Structures

#### 1. TermDefinition Enhancement

Added lineage tracking fields:
```python
# NEW FIELDS
depends_on: List[str]  # IDs of other terms/formulas referenced
used_by: List[str]  # IDs of formulas/terms that reference this term
inputs: List[TermInput]  # Input parameters used in this definition
```

New `TermInput` dataclass to track input sources.

#### 2. FormulaReference Enhancement

Replaced simple `variables: List[str]` with comprehensive tracking:
```python
# REPLACED
variables: List[str]  # Simple list of variable names

# WITH
variables: List[FormulaVariable]  # Variables with source tracking
parameters: List[FormulaParameter]  # Parameters with source tracking
depends_on: List[str]  # All dependencies
used_by: List[str]  # All dependents
```

New dataclasses:
- `FormulaVariable`: Tracks variable name, source entity, description, whether derived
- `FormulaParameter`: Tracks parameter name, value, source entity, description

#### 3. TableData Enhancement

Added parameter tracking:
```python
# NEW FIELDS
provides_parameters: List[TableParameter]  # Parameters defined in table
used_by: List[str]  # Formulas/terms using this table's data
```

New `TableParameter` dataclass with row/column tracking.

#### 4. DocumentIR Enhancement

Added dependency graph and lineage caching:
```python
# NEW FIELDS
dependency_graph: DependencyGraph  # Complete dependency graph
lineage_cache: Dict[str, Lineage]  # Pre-computed lineage

# NEW METHODS
def get_impact_analysis(self, entity_id: str) -> ImpactAnalysis
def get_entity_lineage(self, entity_id: str) -> Lineage
```

#### 5. New Graph Data Structures

- `DependencyGraph`: Complete directed acyclic graph with cycle detection
- `DependencyEdge`: Typed edges with metadata (variable names, parameter names)
- `GraphNode`: Nodes with in/out degree tracking
- `Lineage`: Complete lineage information (ancestors, descendants, depth)

### New Functionality

#### 1. Dependency Graph Builder

Added `DependencyGraphBuilder` class that:
- Constructs complete dependency graph from semantic entities
- Links variables/parameters to their sources
- Computes forward and backward lineage
- Detects circular dependencies
- Performs topological sort

#### 2. Enhanced Validation

Updated validation layer to include:
- Dependency graph construction
- Lineage computation (forward/backward tracking)
- Impact analysis (change propagation)
- Orphaned term detection
- Missing parameter source detection

#### 3. Enhanced LLM-Ready Format

Updated output format to include:
- Source information for each variable/parameter
- Direct and transitive dependencies
- Usage information (what uses this entity)
- Dependency depth
- Complete dependency graph summary
- Critical path analysis
- Pre-computed impact analysis

### Documentation Enhancements

#### 1. Use Cases Section (NEW)

Added 6 detailed use cases demonstrating lineage tracking:
1. **Impact Analysis**: What changes if a parameter is modified?
2. **Variable Source Tracking**: Where does this variable come from?
3. **Missing Definition Detection**: Are all variables defined?
4. **Circular Dependency Detection**: Are there any cycles?
5. **Documentation Completeness**: Are there orphaned terms?
6. **Change Validation**: What uses this formula?

Each use case includes:
- Scenario description
- Example query
- Detailed response showing lineage information

#### 2. Example Dependency Chain

Added concrete example showing:
```
Table_1 → Formula_3 → Formula_7 → Term_5
```

With complete lineage information:
- Direct dependencies
- Transitive dependencies
- Direct dependents
- Transitive dependents
- Dependency depth

#### 3. JSON Serialization Example

Added complete JSON example showing how `Formula_7` is serialized with:
- All variables with source tracking
- All parameters with source tracking
- Complete lineage information
- Dependency lists

### Updated Consequences

Enhanced positive consequences to include:
- Comprehensive dependency tracking capabilities
- Parameter lineage tracking from source to usage
- Change impact analysis
- Full provenance for audit trails

## Benefits

### 1. Complete Traceability

Every entity can trace its complete lineage:
- **Backward**: Where do my inputs come from?
- **Forward**: What uses my outputs?
- **Transitive**: Complete ancestor/descendant chains

### 2. Robust Validation

Pre-compute validation before AI analysis:
- Detect undefined variables before running expensive LLM calls
- Identify circular dependencies that would cause infinite loops
- Find orphaned definitions that indicate documentation issues
- Verify all parameter sources exist

### 3. Impact Analysis

Answer critical questions:
- "If I change this parameter, what is affected?"
- "Can I safely modify this formula?"
- "What downstream entities need retesting?"

### 4. Better AI Analysis

LLMs receive enriched input:
- Pre-computed dependency information
- Source attribution for all variables
- Impact analysis summary
- Validation results

This reduces hallucination risk and improves analysis quality.

### 5. Audit and Compliance

Full lineage tracking provides:
- Complete provenance for all calculations
- Traceable parameter sources
- Reproducible extraction results
- Change impact documentation

## Implementation Notes

### Data Structure Size

Each formula now includes:
- Variables: ~50-200 bytes each (with source tracking)
- Parameters: ~50-150 bytes each
- Lineage: ~100-300 bytes
- Dependencies: ~20-50 bytes per dependency

For a typical document with 50 formulas:
- Previous: ~10-20 KB
- Enhanced: ~50-100 KB
- Increase: ~3-5x

This is acceptable as the data is JSON-serializable and compressible.

### Performance Considerations

- **Graph construction**: O(V + E) where V = entities, E = dependencies
- **Lineage computation**: O(V + E) per entity with caching
- **Cycle detection**: O(V + E) using DFS
- **Impact analysis**: O(V) using pre-computed lineage

For typical documents (100-500 entities):
- Graph construction: <100ms
- Full lineage computation: <200ms
- Total overhead: <500ms

### Backward Compatibility

The enhancement is backward compatible:
- All new fields are optional (can be empty lists)
- Existing code can ignore lineage fields
- Old IR format can be upgraded by:
  - Adding empty `depends_on`/`used_by` lists
  - Converting `variables: List[str]` to `List[FormulaVariable]`
  - Building dependency graph post-hoc

## Testing Strategy

Tests should cover:

1. **Variable Source Tracking**
   - Variables from tables
   - Variables from formulas (derived)
   - Variables from terms
   - Undefined variables

2. **Parameter Tracking**
   - Parameters from tables (with row/column)
   - Inline constants
   - Parameter values

3. **Dependency Graph**
   - Edge creation
   - Parent/child queries
   - Ancestor/descendant queries
   - Cycle detection
   - Topological sort

4. **Lineage Computation**
   - Direct dependencies
   - Transitive dependencies
   - Dependency depth
   - Critical path finding

5. **Impact Analysis**
   - Direct impact
   - Transitive impact
   - Multi-level propagation

6. **Validation**
   - Undefined variable detection
   - Circular dependency detection
   - Orphaned term detection
   - Missing source detection

## Migration Plan

### Phase 1: Update Data Structures (Week 1)
- Implement enhanced dataclasses
- Add migration functions for old → new format
- Update serialization/deserialization

### Phase 2: Implement Graph Builder (Week 1-2)
- Implement `DependencyGraphBuilder`
- Implement `DependencyGraph` with all operations
- Add cycle detection and topological sort

### Phase 3: Update Extractors (Week 2-3)
- Update formula extractor to track variable sources
- Update table extractor to identify provided parameters
- Update term extractor to track inputs

### Phase 4: Implement Validation (Week 3)
- Implement undefined variable detection
- Implement circular dependency detection
- Implement orphaned term detection
- Implement missing source detection

### Phase 5: Update LLM Format (Week 4)
- Update `to_llm_format()` to include dependency info
- Add dependency graph summary section
- Add impact analysis section

### Phase 6: Testing and Documentation (Week 4)
- Comprehensive test suite
- Performance benchmarks
- User documentation
- API documentation

## Related Documents

- [ADR-014: Semantic Intermediate Representation](../decisions/014-semantic-intermediate-representation.md) - Updated ADR
- [ADR-013: LaTeX Formula Preservation](../decisions/013-latex-formula-preservation.md) - Formula extraction
- [ADR-004: Document Format Conversion](../decisions/004-document-format-conversion.md) - Conversion pipeline

## Success Metrics

- **Coverage**: 100% of variables tracked to sources
- **Validation**: Detect 100% of circular dependencies
- **Performance**: <500ms overhead for typical documents
- **Completeness**: Full lineage for all entities
- **Accuracy**: Zero false positives in undefined variable detection
