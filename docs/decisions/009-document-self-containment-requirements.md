# ADR-009: Document Self-Containment Requirements

## Status

Accepted

## Date

2025-12-07

## Context

Trading algorithm documentation must be complete enough that an independent person can fully implement the strategy without requiring any external references or making assumptions. This is critical for:

1. **Regulatory Compliance**: Index methodology documents must be transparent and reproducible for regulatory review
2. **Operational Continuity**: Teams must be able to implement strategies from documentation alone
3. **Audit Requirements**: Complete audit trails require documents that are self-explanatory
4. **Risk Management**: Ambiguous or incomplete documentation can lead to implementation errors

The existing AI analysis needed enhancement to specifically target self-containment issues that would block independent implementation or prevent exact index calculation.

## Decision

We implement strict self-containment requirements for document analysis with the following components:

### 1. Zero Tolerance Policy for Assumptions

The AI analysis will flag ANY content that requires inference or assumption to understand. This includes:
- Undefined parameters, thresholds, or weights
- References to external documents not included
- Vague methodology descriptions
- Generic data source references

### 2. New Issue Categories

The following issue categories are introduced for self-containment analysis:
- `missing_reference`: External document/appendix referenced but not included
- `undefined_parameter`: Parameter/threshold/value mentioned but not defined
- `incomplete_formula`: Formula missing components or specifications
- `ambiguous_methodology`: Process lacking implementation detail
- `external_dependency`: Reliance on unspecified external systems
- `assumption_required`: Information requiring inference to understand
- `inconsistent_content`: Conflicting information within/across documents
- `missing_governance`: Governance process not fully documented
- `data_source_unspecified`: Data source mentioned without full specification
- `compliance_gap`: Regulatory/policy compliance issue

### 3. Structured Analysis Output

Analysis responses include new structured fields:
- `missing_documents`: List of referenced but not included documents
- `undefined_dependencies`: External systems/data feeds requiring specification
- `implementation_gaps`: Gaps affecting index calculation or strategy implementation
- `self_containment_score`: Numeric score (0.0-1.0) for self-containment
- `implementability_assessment`: Assessment of whether strategy can be independently implemented

### 4. Implementation Criteria

An independent person with access ONLY to the uploaded documents must be able to:
1. Fully understand and implement the trading strategy
2. Calculate the EXACT same index level as the original authors
3. Execute all trading decisions, rebalancing, and governance procedures
4. Access ALL required data sources, formulas, parameters, and thresholds

## Consequences

### Positive

- Documents that pass analysis are guaranteed to be implementable
- Clear feedback on exactly what is missing for self-containment
- Structured output enables systematic tracking of documentation gaps
- Self-containment score provides quantifiable metric for document quality
- Reduces operational risk from ambiguous documentation

### Negative

- Stricter requirements may initially result in more issues being flagged
- Existing documents may need significant updates to meet requirements
- Additional computational cost for more comprehensive analysis

### Neutral

- Requires training users on new issue categories
- Policy repositories may need updates to include self-containment rules
- Test fixtures created to validate issue detection

## Alternatives Considered

### 1. Lighter Touch Validation

Only flag obviously missing information without strict self-containment enforcement.

**Not chosen because**: Would not catch subtle gaps that could cause implementation errors.

### 2. Manual Checklists

Provide checklists for document authors to self-certify completeness.

**Not chosen because**: Prone to human error and doesn't provide actionable feedback.

### 3. Template-Based Validation

Require strict document templates with mandatory sections.

**Not chosen because**: Too rigid and doesn't account for varying document structures across different trading strategies.

## References

- Document Analysis Prompt: `src/infrastructure/ai/prompts/document_analysis.py`
- Policy Compliance Prompt: `src/infrastructure/ai/prompts/policy_compliance.py`
- Test Fixtures: `tests/fixtures/sample_docs/`
- E2E Tests: `tests/integration/test_self_containment_e2e.py`
