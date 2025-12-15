# Change Log: End-to-End Test Suite for Document Analysis Pipeline

## Date
2025-12-15

## Author
Claude Code (Sonnet 4.5)

## Summary
Implemented comprehensive end-to-end tests that process all 20 test documents in `/workspaces/data/test_documents` through the full conversion and analysis pipeline, validating that the system correctly identifies the issues documented in the corresponding JSON files.

## Changes

### New Files
- `/workspaces/tests/integration/test_document_suite_e2e.py` - Comprehensive end-to-end test suite (620 lines)
  - Parametrized tests that process all 20 .docx test documents
  - Validates detected issues against expected issues from JSON files
  - Specialized tests for different issue categories:
    - Clean documents with minimal issues
    - Critical issue detection
    - Market calendar issues
    - Undefined parameters
    - Formula issues
    - Worst-case scenarios

### Modified Files
- `/workspaces/src/api/routes/auth.py`
  - Fixed import bug: changed `from src.api.dependencies.auth import get_current_user` to `from src.api.dependencies import get_current_user`
  - The `dependencies` module is a single file, not a package

## Implementation Details

### Test Suite Architecture

The test suite implements a comprehensive end-to-end validation framework:

#### 1. Test Document Discovery
```python
def get_test_documents() -> List[Dict[str, Any]]:
    """Load all test documents and their expected results."""
    # Discovers all .docx files in /workspaces/data/test_documents
    # Loads corresponding .json files with expected issues
    # Returns structured test data for parametrization
```

#### 2. Main Parametrized Test
```python
@pytest.mark.parametrize("test_doc", test_documents, ids=test_ids)
async def test_document_analysis(self, client, policy_repository, test_doc):
    """Test full document analysis pipeline for each test document."""
    # 1. Upload .docx file via POST /api/v1/documents
    # 2. Assign to policy repository via PUT /api/v1/documents/{id}/policy-repository
    # 3. Trigger analysis via POST /api/v1/documents/{id}/analyze
    # 4. Retrieve feedback via GET /api/v1/documents/{id}/feedback
    # 5. Validate detected issues against expected issues
```

#### 3. Issue Validation Strategy

The validation allows for AI variability while ensuring quality:

- **Issue Count Tolerance**:
  - Low complexity: ±2 issues variance allowed
  - Medium/High complexity: ±3 issues variance allowed

- **Critical Issue Detection**:
  - Must detect ≥80% of critical issues
  - Critical issues are the highest priority for compliance

- **Category-Specific Validation**:
  - Market calendar issues detection
  - Undefined parameters detection
  - Formula issues detection

### Test Coverage

The test suite covers all 20 test documents:

1. **doc_01_clean** - Nearly perfect document (baseline)
2. **doc_02_missing_appendix** - Missing external references
3. **doc_03_undefined_parameters** - 12 undefined parameter issues
4. **doc_04_incomplete_formulas** - Mathematical formula issues
5. **doc_05_market_calendar** - Market calendar ambiguities (CRITICAL)
6. **doc_06_external_dependencies** - Unidentified external systems
7. **doc_07_missing_governance** - Governance gaps
8. **doc_08_inconsistent** - Internal contradictions
9. **doc_09_ambiguous** - Vague methodology descriptions
10. **doc_10_missing_risks** - Missing risk disclosures
11. **doc_11_perfect_compliance** - Zero issues (perfect document)
12. **doc_12_formula_precision** - Formula precision issues
13. **doc_13_data_gaps** - Data specification gaps
14. **doc_14_complex_multi** - Complex multi-issue document
15. **doc_15_simple_fix** - Simple fixable issues
16. **doc_16_calendar_complex** - Complex calendar handling
17. **doc_17_moderate** - Moderate complexity
18. **doc_18_edge_cases** - Edge case scenarios
19. **doc_19_almost_clean** - Nearly compliant
20. **doc_20_worst_case** - Maximum issues (stress test)

### Specialized Tests

Beyond the parametrized test, the suite includes targeted tests:

1. **test_clean_document_minimal_issues** - Validates clean documents (doc_01, doc_11) have minimal false positives

2. **test_critical_issues_detected** - Ensures all documents with critical issues are properly flagged

3. **test_worst_case_document** - Stress tests the system with doc_20 (maximum issues)

4. **test_market_calendar_issues** - Validates detection of calendar-related issues (doc_05, doc_16) per ADR-018

5. **test_undefined_parameters_detection** - Validates detection of undefined parameters (doc_03)

6. **test_formula_issues_detection** - Validates detection of incomplete formulas (doc_04, doc_12)

## Test Execution

### Prerequisites
- PostgreSQL database running (Docker Compose)
- AI provider API key (ANTHROPIC_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY)
- Environment variables set (can use doppler)

### Running the Tests

```bash
# Start PostgreSQL database
docker compose up -d

# Run all document suite tests
PYTHONPATH=/workspaces doppler run -- poetry run pytest tests/integration/test_document_suite_e2e.py -v

# Run specific test for one document
PYTHONPATH=/workspaces doppler run -- poetry run pytest \
  "tests/integration/test_document_suite_e2e.py::TestDocumentSuiteE2E::test_document_analysis[doc_01_clean]" -xvs

# Run clean document tests only
PYTHONPATH=/workspaces doppler run -- poetry run pytest \
  tests/integration/test_document_suite_e2e.py::TestDocumentSuiteE2E::test_clean_document_minimal_issues -xvs

# Run market calendar tests
PYTHONPATH=/workspaces doppler run -- poetry run pytest \
  tests/integration/test_document_suite_e2e.py::TestDocumentSuiteE2E::test_market_calendar_issues -xvs
```

## Known Issues

### Event Store SQL Bug
The tests revealed a pre-existing bug in the event store implementation:

**Error**: `asyncpg.exceptions.FeatureNotSupportedError: FOR UPDATE is not allowed with aggregate functions`

**Location**: `/workspaces/src/infrastructure/persistence/event_store.py:75`

**Impact**: This prevents the tests from completing the full workflow. The test infrastructure is correct and successfully:
- Connects to the API
- Uploads documents
- Creates policy repositories
- Calls the analysis endpoints

The failure occurs in the event store when trying to save aggregates.

**Recommendation**: Fix the SQL query in event_store.py that combines aggregate functions with FOR UPDATE locking.

## Rationale

This comprehensive test suite is essential for:

1. **Regression Testing**: Ensure document analysis quality doesn't degrade over time
2. **AI Provider Comparison**: Compare performance of different AI models (Gemini, Claude, OpenAI)
3. **Quality Benchmarking**: Establish baseline detection rates for different issue types
4. **Release Validation**: Verify full pipeline works before deployment
5. **Performance Testing**: Identify bottlenecks in document processing

The test documents cover the full spectrum from perfect (doc_11) to worst-case (doc_20), providing comprehensive validation.

## Related Files

### Test Documents
- `/workspaces/data/test_documents/*.docx` - 20 test DOCX files
- `/workspaces/data/test_documents/*.json` - 20 expected issue JSON files
- `/workspaces/data/test_documents/README.md` - Documentation of test document suite

### Related Tests
- `/workspaces/tests/integration/test_analysis_flow_e2e.py` - Analysis workflow tests
- `/workspaces/tests/integration/test_document_upload_e2e.py` - Document upload tests
- `/workspaces/tests/integration/test_feedback_flow_e2e.py` - Feedback workflow tests
- `/workspaces/tests/integration/test_self_containment_e2e.py` - Self-containment tests

### Related ADRs
- [ADR-004: Document Format Conversion](../decisions/004-document-format-conversion.md) - Conversion pipeline
- [ADR-014: Semantic Intermediate Representation](../decisions/014-semantic-intermediate-representation.md) - IR layer
- [ADR-018: Market Calendar Validation Framework](../decisions/018-market-calendar-validation.md) - Calendar issue detection

## Next Steps

1. **Fix Event Store Bug**: Resolve the FOR UPDATE + aggregate function SQL error
2. **Run Full Test Suite**: Execute all 20 document tests to establish baseline metrics
3. **Add Performance Metrics**: Track processing time per document
4. **Add Confidence Score Validation**: Validate confidence scores are in reasonable ranges
5. **Add Self-Containment Score Tests**: Validate self-containment scoring accuracy
6. **CI/CD Integration**: Add these tests to continuous integration pipeline
7. **Test Report Generation**: Generate HTML reports showing detection rates per issue category
8. **Add Test Data Versioning**: Version test documents and expected results for reproducibility
