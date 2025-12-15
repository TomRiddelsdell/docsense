# Test Document Suite

## Overview

This directory contains 20 Word (.docx) test documents and corresponding JSON metadata files designed to comprehensively test the AI-Powered Trading Algorithm Specification Platform's document analysis and issue detection capabilities.

## Document Catalog

### Documents 01-05: Baseline + Primary Issue Categories

#### Document 01: Clean Baseline
- **File**: `doc_01_clean.docx`
- **Title**: S&P Technology Sector Equal Weight Index
- **Complexity**: Low
- **Issue Count**: 1 (low severity)
- **Purpose**: Nearly perfect document serving as baseline reference
- **Key Features**: Complete specifications, proper data sources, clear methodology
- **Use Case**: Validate system doesn't generate false positives on well-specified documents

#### Document 02: Missing References
- **File**: `doc_02_missing_appendix.docx`
- **Title**: Emerging Markets Dividend Growth Strategy
- **Complexity**: Medium
- **Issue Count**: 4 (critical)
- **Primary Issue**: Missing external references
- **Key Detections**: References Appendix A, B, C that don't exist; mentions external documents not provided
- **Use Case**: Test detection of missing appendices and external dependencies

#### Document 03: Undefined Parameters
- **File**: `doc_03_undefined_parameters.docx`
- **Title**: Low Volatility Equity Portfolio Strategy
- **Complexity**: High
- **Issue Count**: 12 (critical/high)
- **Primary Issue**: Parameters referenced but not defined
- **Key Detections**: "Low volatility" threshold undefined, "sufficient liquidity" not quantified, "reasonable" tracking error subjective
- **Use Case**: Test detection of vague quantitative requirements

#### Document 04: Incomplete Formulas
- **File**: `doc_04_incomplete_formulas.docx`
- **Title**: Momentum Factor Index Methodology
- **Complexity**: High
- **Issue Count**: 10 (critical/high)
- **Primary Issue**: Mathematical formulas missing critical components
- **Key Detections**: Lookback periods missing, calculation frequencies unspecified, normalization methods undefined
- **Use Case**: Test mathematical specification completeness validation

#### Document 05: Market Calendar Issues ⚠️ CRITICAL
- **File**: `doc_05_market_calendar.docx`
- **Title**: Global Multi-Asset Tactical Allocation Strategy
- **Complexity**: High
- **Issue Count**: 11 (critical)
- **Primary Issue**: Market calendar and holiday handling ambiguities
- **Key Detections**: "Business day" undefined, holiday handling missing, rebalancing date ambiguities
- **Use Case**: Test ADR-018 Market Calendar Validation Framework
- **Note**: Directly addresses #1 source of implementation failures per ADR-018

### Documents 06-10: Secondary Issue Categories

#### Document 06: External Data Dependencies
- **File**: `doc_06_external_dependencies.docx`
- **Title**: Credit Spread Trading Strategy
- **Complexity**: Medium
- **Issue Count**: 8 (critical/high)
- **Primary Issue**: External systems and data feeds not identified
- **Key Detections**: "Pricing vendor" not named, "rating agency" unspecified, "analytics platform" undefined
- **Use Case**: Test detection of unidentified external system dependencies

#### Document 07: Missing Governance
- **File**: `doc_07_missing_governance.docx`
- **Title**: Quantitative Equity Long-Short Strategy
- **Complexity**: Medium
- **Issue Count**: 9 (critical/high)
- **Primary Issue**: Governance, approval processes, and oversight procedures missing
- **Key Detections**: No approval authority specified, no exception handling process, no audit procedures
- **Use Case**: Test governance gap detection

#### Document 08: Inconsistent Content
- **File**: `doc_08_inconsistent.docx`
- **Title**: Quality Dividend Growth Index
- **Complexity**: Low
- **Issue Count**: 6 (critical)
- **Primary Issue**: Internal contradictions within document
- **Key Detections**: Section 1 requires "10 years" but Section 2 requires "5 years"; dividend yield ranges contradict; weighting methodology contradicts
- **Use Case**: Test internal consistency validation

#### Document 09: Ambiguous Methodology
- **File**: `doc_09_ambiguous.docx`
- **Title**: ESG Enhanced Index Strategy
- **Complexity**: Medium
- **Issue Count**: 11 (critical/high)
- **Primary Issue**: Vague methodology descriptions without specifics
- **Key Detections**: "Strong ESG scores" undefined, "controversial activities" not specified, "reasonable tracking error" subjective
- **Use Case**: Test detection of subjective/ambiguous language

#### Document 10: Missing Risk Disclosures
- **File**: `doc_10_missing_risks.docx`
- **Title**: Leveraged Growth Stock Strategy
- **Complexity**: Low
- **Issue Count**: 5 (critical/high)
- **Primary Issue**: Compliance gaps - missing required risk disclosures
- **Key Detections**: Leverage risks not disclosed, concentration risk not mentioned, no downside scenario discussion
- **Use Case**: Test regulatory compliance gap detection
- **Compliance Status**: Non-compliant for investor documents

### Documents 11-15: Quality Spectrum

#### Document 11: Perfect Compliance ⭐
- **File**: `doc_11_perfect_compliance.docx`
- **Title**: Russell 2000 Equal Weight Index - Methodology Document
- **Complexity**: Low
- **Issue Count**: 0
- **Purpose**: Exemplary document with complete specifications
- **Key Features**: All data sources named, all parameters defined, risk disclosures present, precise rebalancing rules
- **Use Case**: Gold standard reference; validate system correctly identifies compliant documents
- **Self-Containment Score**: 0.98
- **Implementability Score**: 0.98

#### Document 12: Formula Precision Issues
- **File**: `doc_12_formula_precision.docx`
- **Title**: Quantitative Mean Reversion Strategy
- **Complexity**: High
- **Issue Count**: 8 (critical/high)
- **Primary Issue**: Formulas lack necessary precision for implementation
- **Key Detections**: Lookback periods missing from formulas, thresholds not quantified, calculation timing unclear
- **Use Case**: Test mathematical precision validation

#### Document 13: Data Specification Gaps
- **File**: `doc_13_data_gaps.docx`
- **Title**: Emerging Markets Local Currency Bond Strategy
- **Complexity**: Medium
- **Issue Count**: 7 (critical/high)
- **Primary Issue**: Data sources and specifications incomplete
- **Key Detections**: Market classification source missing, pricing service unidentified, rating agency not specified
- **Use Case**: Test data source specification completeness

#### Document 14: Multi-Issue Complex
- **File**: `doc_14_complex_multi.docx`
- **Title**: Global Macro Tactical Asset Allocation Model
- **Complexity**: High
- **Issue Count**: 15 (critical/medium)
- **Primary Issue**: Severe underspecification across multiple dimensions
- **Key Detections**: Undefined asset classes, unspecified indicators, missing formulas, vague governance
- **Use Case**: Test system's ability to identify and categorize diverse issues in severely flawed document
- **Self-Containment Score**: 0.15
- **Implementability Score**: 0.10
- **Note**: Requires comprehensive revision to be implementable

#### Document 15: Simple Fixes
- **File**: `doc_15_simple_fix.docx`
- **Title**: U.S. Treasury Bond Index
- **Complexity**: Low
- **Issue Count**: 3 (low severity)
- **Primary Issue**: Minor ambiguities easily resolved
- **Key Detections**: Range endpoint ambiguity, time specification could be clearer
- **Use Case**: Test system distinguishes minor vs critical issues
- **Self-Containment Score**: 0.92
- **Implementability Score**: 0.90
- **Note**: Production-ready with minor clarifications

### Documents 16-20: Specialized & Edge Cases

#### Document 16: Complex Calendar Issues ⚠️
- **File**: `doc_16_calendar_complex.docx`
- **Title**: Asia-Pacific Multi-Market Strategy
- **Complexity**: High
- **Issue Count**: 12 (critical/medium)
- **Primary Issue**: Multi-timezone and multi-market calendar coordination
- **Key Detections**: Timezone coordination missing, holiday handling across markets undefined, DST not addressed, simultaneous rebalancing impossible
- **Use Case**: Advanced test of ADR-018 Market Calendar Framework
- **Note**: Critical example of complex calendar issues that cause implementation failures

#### Document 17: Moderate Complexity
- **File**: `doc_17_moderate.docx`
- **Title**: U.S. Dividend Aristocrats Index
- **Complexity**: Medium
- **Issue Count**: 5 (medium/high)
- **Primary Issue**: Balanced mix of issues with moderate severity
- **Key Detections**: Weighting formula incomplete, thresholds undefined, timing not specified
- **Use Case**: Test system on realistic documents with typical issue density
- **Self-Containment Score**: 0.65
- **Implementability Score**: 0.60

#### Document 18: Edge Cases
- **File**: `doc_18_edge_cases.docx`
- **Title**: Covered Call Writing Strategy
- **Complexity**: High
- **Issue Count**: 9 (critical/medium)
- **Primary Issue**: Failure to specify edge case handling
- **Key Detections**: Early assignment not addressed, corporate actions not specified, odd lots not handled
- **Use Case**: Test detection of missing edge case specifications
- **Note**: Would encounter operational issues in real-world execution

#### Document 19: Almost Clean ✓
- **File**: `doc_19_almost_clean.docx`
- **Title**: Bloomberg Barclays U.S. Aggregate Bond Index Replication
- **Complexity**: Low
- **Issue Count**: 2 (low severity)
- **Primary Issue**: Minimal issues, essentially production-ready
- **Key Detections**: Minor measurement window ambiguity, slight range imprecision
- **Use Case**: Validate system correctly identifies near-perfect documents
- **Self-Containment Score**: 0.93
- **Implementability Score**: 0.92

#### Document 20: Worst Case Scenario 🚨
- **File**: `doc_20_worst_case.docx`
- **Title**: Experimental Cryptocurrency Momentum Strategy
- **Complexity**: High
- **Issue Count**: 20 (critical/high/medium)
- **Primary Issue**: Severely problematic across all dimensions
- **Key Detections**: No asset definitions, no risk disclosures, completely undefined methodology, regulatory non-compliance, missing all governance
- **Use Case**: Test system's ability to flag documents unsuitable for implementation
- **Compliance Status**: NON-COMPLIANT - unsuitable for investor presentation
- **Self-Containment Score**: 0.10
- **Implementability Score**: 0.05
- **Note**: Comprehensive rewrite required before implementation possible

## Issue Category Coverage

### Issue Types Tested

| Category | Documents | Count |
|----------|-----------|-------|
| `missing_reference` | 02 | 4 |
| `undefined_parameter` | 03, 06, 07, 09, 10, 12, 13, 14, 15, 17, 18, 20 | 45+ |
| `incomplete_formula` | 04, 12, 14 | 15 |
| `market_calendar` | 05, 16 | 23 |
| `external_dependency` | 06, 14, 20 | 13 |
| `missing_governance` | 07, 11, 14, 16 | 13 |
| `inconsistent_content` | 08 | 6 |
| `ambiguous_methodology` | 09, 12, 13, 14, 15, 16, 17, 18, 19, 20 | 30+ |
| `compliance_gap` | 10, 14, 20 | 9 |
| `data_source_unspecified` | 09, 13, 14, 16, 20 | 14 |

### Severity Distribution

| Severity | Document Count | Total Issues |
|----------|----------------|--------------|
| Critical | 18 docs | 95+ issues |
| High | 14 docs | 40+ issues |
| Medium | 10 docs | 20+ issues |
| Low | 4 docs | 6 issues |

### Complexity Distribution

| Complexity | Document Count | Avg Issues |
|------------|----------------|------------|
| Low | 6 docs | 2.5 |
| Medium | 7 docs | 7.1 |
| High | 7 docs | 12.4 |

## Self-Containment Scores

Documents ranked by self-containment (ability to implement without external clarification):

1. **doc_11**: 0.98 - Perfect compliance
2. **doc_01**: 0.95 - Nearly perfect baseline
3. **doc_19**: 0.93 - Almost clean
4. **doc_15**: 0.92 - Simple fixes needed
5. **doc_17**: 0.65 - Moderate
6. **doc_10**: 0.60 - Missing risks
7. **doc_08**: 0.50 - Inconsistencies
8. **doc_18**: 0.40 - Edge cases
9. **doc_07**: 0.40 - Governance gaps
10. **doc_12**: 0.40 - Formula precision
11. **doc_13**: 0.35 - Data gaps
12. **doc_04**: 0.35 - Incomplete formulas
13. **doc_03**: 0.30 - Undefined parameters
14. **doc_06**: 0.30 - External dependencies
15. **doc_09**: 0.25 - Ambiguous methodology
16. **doc_05**: 0.25 - Calendar issues
17. **doc_16**: 0.25 - Complex calendar
18. **doc_02**: 0.20 - Missing references
19. **doc_14**: 0.15 - Multi-issue complex
20. **doc_20**: 0.10 - Worst case

## Usage Recommendations

### For Demos

**Quick Demo (5 minutes)**:
1. Show **doc_01** (clean baseline) - system correctly validates good document
2. Show **doc_08** (inconsistent) - system catches contradictions
3. Show **doc_05** (calendar issues) - demonstrate critical market calendar detection (ADR-018)

**Standard Demo (15 minutes)**:
1. **doc_11** - Perfect document (validate no false positives)
2. **doc_03** - Undefined parameters (common issue)
3. **doc_05** - Calendar issues (critical per ADR-018)
4. **doc_09** - Ambiguous methodology (show severity differentiation)
5. **doc_20** - Worst case (show comprehensive issue detection)

**Comprehensive Demo (30 minutes)**:
- Show progression: 11 (perfect) → 19 (almost clean) → 17 (moderate) → 14 (complex) → 20 (worst)
- Demonstrate all issue categories
- Show self-containment scoring
- Highlight compliance gap detection (doc 10, doc 20)

### For Testing

**Smoke Test** (validate basic functionality):
- doc_01, doc_08, doc_11, doc_20

**Regression Test** (comprehensive validation):
- All 20 documents

**Issue Category Testing** (validate specific detectors):
- Missing references: doc_02
- Undefined parameters: doc_03, doc_06
- Formulas: doc_04, doc_12
- Calendar: doc_05, doc_16 (ADR-018)
- Governance: doc_07
- Consistency: doc_08
- Ambiguity: doc_09
- Compliance: doc_10, doc_20
- Data sources: doc_13

**Precision Testing** (validate severity assessment):
- Low severity: doc_15, doc_19
- Medium severity: doc_06, doc_07, doc_17
- High severity: doc_03, doc_04, doc_09
- Critical severity: doc_05, doc_14, doc_16, doc_20

### For Development

**Feature Development**:
- Use doc_11 as reference for perfect document structure
- Use doc_14 and doc_20 for stress testing
- Use doc_05 and doc_16 for calendar logic (ADR-018)

**Accuracy Validation**:
- Compare AI detection results to metadata JSON files
- Validate confidence scores align with actual ambiguity
- Test that severity levels match metadata severity

## Metadata Schema

Each JSON file contains:

```json
{
  "document_id": "unique_identifier",
  "title": "Document Title",
  "version": "1.0",
  "created_date": "ISO 8601 timestamp",
  "complexity": "low|medium|high",
  "issue_count": 0-20,
  "issues": [
    {
      "severity": "critical|high|medium|low",
      "category": "issue_category",
      "title": "Brief issue description",
      "description": "Detailed explanation",
      "location": "Section reference",
      "original_text": "Problematic text (if applicable)",
      "suggested_fix": "Concrete recommendation",
      "confidence": 0.0-1.0
    }
  ],
  "undefined_dependencies": [...],
  "missing_documents": [...],
  "implementation_gaps": [...],
  "self_containment_score": 0.0-1.0,
  "implementability_score": 0.0-1.0,
  "compliance_assessment": {...},
  "notes": "Additional context"
}
```

## Key Insights

### Critical Priorities (ADR-018)

Market calendar issues (doc_05, doc_16) represent the **#1 source of implementation failures** according to ADR-018. These documents specifically test:
- Holiday handling across markets
- Timezone coordination
- Business day definitions
- Rebalancing date ambiguities
- DST transitions

### Validation Strategy

The test suite enables validation of:

1. **Detection Accuracy**: Compare AI findings to JSON metadata
2. **Severity Assessment**: Validate critical issues flagged as critical
3. **False Positive Rate**: Docs 01, 11, 19 should generate minimal issues
4. **False Negative Rate**: Docs 14, 20 should detect all major issues
5. **Consistency**: Multiple runs should produce consistent results
6. **Completeness**: All issue categories covered

### Expected System Behavior

**Excellent System Performance**:
- doc_01, doc_11, doc_19: ≤3 total issues detected
- doc_20: ≥18 issues detected across multiple categories
- doc_05, doc_16: All critical calendar issues flagged
- Self-containment scores within ±0.10 of metadata values

**Acceptable System Performance**:
- ≤2 false positives per document for clean docs
- ≥80% detection rate for critical issues in problematic docs
- Severity classification within ±1 level of metadata

## File Statistics

- **Total Documents**: 20 (.docx files)
- **Total Metadata Files**: 20 (.json files)
- **Total Issues Documented**: 161 across all documents
- **Average Issues per Document**: 8.05
- **Median Issues per Document**: 8
- **Range**: 0-20 issues per document

## Generation Scripts

Generated by:
1. `scripts/generate_test_documents.py` - Documents 01-05
2. `scripts/generate_test_documents_part2.py` - Documents 06-10
3. `scripts/generate_test_documents_part3.py` - Documents 11-20

## Related Documentation

- [ADR-018: Market Calendar Validation Framework](../../docs/decisions/018-market-calendar-validation.md) - Critical priority
- [LLM Prompt Catalog](../../docs/architecture/LLM_PROMPT_CATALOG.md) - AI enhancement recommendations
- [VISION.md](../../docs/VISION.md) - Implementation precision requirements
- [IMPLEMENTATION_PLAN.md](../../docs/IMPLEMENTATION_PLAN.md) - Phases 11-13 testing strategy

---

**Last Updated**: 2024-12-08  
**Version**: 1.0  
**Status**: Complete - All 20 documents generated

---

## Semantic IR Enhancement (2025-12-15)

All JSON metadata files have been enhanced with `expected_semantic_ir` fields containing the expected semantic representation for each document. This enables automated testing of the Semantic Intermediate Representation (IR) extraction pipeline per ADR-014.

### JSON File Structure

Each JSON file now includes:

```json
{
  "document_id": "doc_04_incomplete_formulas",
  "title": "Momentum Factor Index Methodology",
  "version": "1.0",
  "complexity": "medium",
  "issue_count": 10,
  "issues": [...],
  "expected_semantic_ir": {
    "definitions": [...],
    "formulae": [...],
    "tables": [...],
    "cross_references": [...]
  }
}
```

### Semantic Content by Document

#### Documents with Formulas (3 total)
- **doc_01_clean**: 3 formulas (index calculation formulas)
- **doc_04_incomplete_formulas**: 4 formulas (momentum, risk-adjusted, composite score, weights)
- **doc_12_formula_precision**: 1 formula

#### Documents with Definitions (10 total)
- **doc_01_clean**: 5 definitions
- **doc_02_missing_appendix**: 2 definitions
- **doc_03_undefined_parameters**: 3 definitions
- **doc_04_incomplete_formulas**: 4 definitions
- **doc_05_market_calendar**: 3 definitions
- **doc_06_external_dependencies**: 1 definition
- **doc_07_missing_governance**: 1 definition
- **doc_08_inconsistent**: 1 definition
- **doc_10_missing_risks**: 1 definition

#### Documents with Cross-References (1 total)
- **doc_02_missing_appendix**: 4 cross-references (to Appendix A, B, C)

#### Documents with Tables (0 total)
- None of the current test documents contain tables
- Future test documents may include parameter tables

### Semantic IR Schema

#### Definition
```json
{
  "id": "term_1",
  "term": "Historical Price",
  "definition": "the price from the lookback period",
  "location": "Paragraph 5",
  "aliases": []
}
```

#### Formula
```json
{
  "id": "formula_1",
  "name": "Momentum Score",
  "expression": "Momentum Score = (Current Price / Historical Price) - 1",
  "location": "Paragraph 4",
  "variables": [
    {"name": "Current", "source": null},
    {"name": "Historical", "source": null},
    {"name": "Price", "source": null}
  ],
  "parameters": []
}
```

#### Table
```json
{
  "id": "table_1",
  "title": "Parameter Schedule",
  "headers": ["Parameter", "Value", "Description"],
  "row_count": 12,
  "column_count": 3,
  "location": "Table 1",
  "is_parameter_table": true,
  "provides_parameters": [
    {"name": "TargetVol", "value": "0.10"}
  ]
}
```

#### Cross-Reference
```json
{
  "id": "ref_1",
  "source_location": "Paragraph 15",
  "target": "Appendix A",
  "reference_text": "see Appendix A"
}
```

### Extraction Methodology

Semantic IR data was extracted using `/workspaces/scripts/enhance_test_jsons_with_semantic_ir.py`:

1. **Formula Extraction**
   - Identifies mathematical expressions using operators: `=`, `×`, `÷`, `/`, `+`, `-`
   - Extracts variable names using regex patterns
   - Captures full formula expressions with context

2. **Definition Extraction**
   - Pattern matching for: `"X" means Y`, `"X" refers to Y`, `X is Y`
   - Handles quoted and unquoted terms
   - Captures definition location for traceability

3. **Table Extraction**
   - Parses all tables in document
   - Identifies parameter tables by header analysis
   - Extracts table structure (rows, columns, headers)
   - Samples parameter values from parameter tables

4. **Cross-Reference Extraction**
   - Identifies references to Sections, Appendices, Tables, Figures
   - Captures reference text and location
   - Enables validation of reference completeness

### Related Test Suites

- **Issue Detection Tests**: `tests/integration/test_document_suite_e2e.py`
  - Validates AI identifies document problems
  - Uses `issues` field from JSON files

- **Semantic IR Tests**: `tests/integration/test_semantic_ir_e2e.py`
  - Validates conversion pipeline extracts semantic structure
  - Uses `expected_semantic_ir` field from JSON files

### Related Documentation

- [ADR-014: Semantic Intermediate Representation](../../docs/decisions/014-semantic-intermediate-representation.md)
- [Change Log: Semantic IR Test Suite](../../docs/changes/2025-12-15-semantic-ir-test-suite.md)
- [Change Log: Test Document Suite E2E](../../docs/changes/2025-12-15-test-document-suite-e2e.md)

### Updating Semantic IR Expectations

If test documents are modified or new documents are added, regenerate semantic IR:

```bash
python3 /workspaces/scripts/enhance_test_jsons_with_semantic_ir.py
```

This will analyze all .docx files and update corresponding JSON files with extracted semantic content.

