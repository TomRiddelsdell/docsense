# Scripts Directory

This directory contains utility scripts for the DocSense Trading Algorithm Document Analyzer project.

## Scripts

### Document Generation

#### `generate_test_documents.py`
Generates test .docx documents for comprehensive testing of the document analysis pipeline.

**Purpose**: Creates trading algorithm specification documents with intentional issues for testing detection capabilities.

**Generated Documents**: Documents 01-07 (baseline and primary issue categories)

**Usage**:
```bash
python3 scripts/generate_test_documents.py
```

#### `generate_test_documents_part2.py`
Generates additional test documents (documents 08-14).

**Purpose**: Creates documents with secondary issue categories (inconsistency, ambiguity, missing risks, data gaps).

**Usage**:
```bash
python3 scripts/generate_test_documents_part2.py
```

#### `generate_test_documents_part3.py`
Generates final batch of test documents (documents 15-20).

**Purpose**: Creates documents with varying complexity levels and edge cases for comprehensive testing.

**Usage**:
```bash
python3 scripts/generate_test_documents_part3.py
```

### Semantic IR Enhancement

#### `enhance_test_jsons_with_semantic_ir.py`
Analyzes .docx test documents and enhances corresponding JSON files with expected semantic representation data.

**Purpose**: Enables automated testing of Semantic Intermediate Representation (IR) extraction per ADR-014.

**What it Does**:
1. Reads each .docx file in `/workspaces/data/test_documents/`
2. Extracts semantic content:
   - **Formulas**: Mathematical expressions with variables
   - **Definitions**: Term definitions using multiple patterns
   - **Tables**: Table structure and parameter extraction
   - **Cross-references**: Internal document references
3. Updates corresponding JSON file with `expected_semantic_ir` field

**Usage**:
```bash
python3 scripts/enhance_test_jsons_with_semantic_ir.py
```

**Output**:
```
======================================================================
Enhancing Test Document JSON Files with Semantic IR
======================================================================

📄 Processing doc_01_clean.docx...
   ✓ Definitions: 5
   ✓ Formulae: 3
   ✓ Tables: 0
   ✓ Cross-references: 0
   ✅ Updated doc_01_clean.json

...

======================================================================
✅ Complete!
======================================================================
```

**Example Output Schema**:
```json
{
  "expected_semantic_ir": {
    "definitions": [
      {
        "id": "term_1",
        "term": "Historical Price",
        "definition": "the price from the lookback period",
        "location": "Paragraph 5",
        "aliases": []
      }
    ],
    "formulae": [
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
    ],
    "tables": [],
    "cross_references": []
  }
}
```

## Extraction Patterns

### Formula Detection
The semantic IR enhancement script identifies formulas using:
- Assignment operators: `=`
- Mathematical symbols: `×`, `÷`, `/`, `+`, `-`, `∑`, `∏`, `√`
- Variable naming patterns: camelCase, PascalCase
- Weight notation: `w1`, `w2`, `w3`

**Example**:
```
Input: "Momentum Score = (Current Price / Historical Price) - 1"
Output: Formula with variables [Current, Price, Historical]
```

### Definition Patterns
Multiple patterns to catch different definition styles:

1. **Formal definitions**: `"Term" means definition`
   - Example: `"Historical Price" means the price from the lookback period`

2. **Reference-style**: `"Term" refers to definition`
   - Example: `"Target Volatility" refers to the annualized volatility target`

3. **Prose definitions**: `Term is definition`
   - Example: `Momentum is calculated by comparing current and historical prices`

4. **Formula context**: `Where Term is definition`
   - Example: `Where Historical Price is the price from the lookback period`

### Table Detection
- Identifies all tables in document
- Extracts headers, row count, column count
- Detects parameter tables by analyzing headers for keywords:
  - "Parameter", "Value", "Description", "Variable"
- Samples up to 5 parameters from parameter tables

### Cross-Reference Detection
Identifies references to:
- Sections: `Section 1`, `Section 2.3`
- Appendices: `Appendix A`, `Appendix B`
- Tables: `Table 1`, `Table 2`
- Figures: `Figure 1`, `Figure 2`

Captures both explicit (`see Section 1`) and implicit references.

## Dependencies

All scripts require:
- Python 3.10+
- `python-docx` library for Word document manipulation
- Standard library: `json`, `re`, `pathlib`

Install dependencies:
```bash
poetry install
```

## Testing Generated Content

After generating or enhancing test documents, run the test suites:

### Document Analysis Tests
```bash
PYTHONPATH=/workspaces doppler run -- poetry run pytest \
  tests/integration/test_document_suite_e2e.py -v
```

### Semantic IR Tests
```bash
PYTHONPATH=/workspaces doppler run -- poetry run pytest \
  tests/integration/test_semantic_ir_e2e.py -v
```

## Related Documentation

- [ADR-014: Semantic Intermediate Representation](../docs/decisions/014-semantic-intermediate-representation.md) - IR architecture
- [ADR-004: Document Format Conversion](../docs/decisions/004-document-format-conversion.md) - Conversion pipeline with AI curation
- [Test Documents README](../data/test_documents/README.md) - Test document catalog
- [Change Log: Semantic IR Test Suite](../docs/changes/2025-12-15-semantic-ir-test-suite.md) - Enhancement details

## Maintenance

### Regenerating Semantic IR
If test documents are modified:

1. Edit the .docx file as needed
2. Run the enhancement script:
   ```bash
   python3 scripts/enhance_test_jsons_with_semantic_ir.py
   ```
3. Review the updated JSON file
4. Run tests to verify changes:
   ```bash
   PYTHONPATH=/workspaces doppler run -- poetry run pytest \
     "tests/integration/test_semantic_ir_e2e.py::TestSemanticIRE2E::test_semantic_ir_extraction[doc_XX]" -xvs
   ```

### Adding New Test Documents
When adding new test documents:

1. Create the .docx file in `/workspaces/data/test_documents/`
2. Manually create the JSON file with issue data
3. Run the enhancement script to add semantic IR
4. Verify the semantic IR is correctly extracted
5. Add any necessary manual corrections to the JSON file
6. Update the test documents README

### Improving Extraction Patterns
To improve semantic extraction accuracy:

1. Edit `enhance_test_jsons_with_semantic_ir.py`
2. Modify extraction patterns in:
   - `extract_formulas()`
   - `extract_definitions()`
   - `extract_tables()`
   - `extract_cross_references()`
3. Test on a single document:
   ```python
   from pathlib import Path
   semantic_ir = analyze_document(Path("path/to/doc.docx"))
   print(json.dumps(semantic_ir, indent=2))
   ```
4. Regenerate all semantic IR
5. Run tests to verify improvements

## Best Practices

### When Creating Test Documents
1. Include diverse semantic content (formulas, definitions, tables)
2. Use standard notation and terminology
3. Follow typical trading algorithm documentation patterns
4. Include both correct and intentionally problematic content
5. Document expected issues in the JSON file

### When Enhancing JSON Files
1. Review extracted semantic IR for accuracy
2. Manually correct any extraction errors
3. Add `aliases` to definitions where appropriate
4. Link `variables` to `source` entities when known
5. Validate JSON structure before committing

### When Modifying Extraction Logic
1. Test on representative documents first
2. Consider both precision (no false positives) and recall (no missed content)
3. Document pattern changes in code comments
4. Update this README with new patterns
5. Run full test suite after changes

## Troubleshooting

### Script Fails to Find Documents
**Error**: `No such file or directory`
**Solution**: Ensure you're running from the workspace root or use absolute paths

### JSON Validation Errors
**Error**: `json.decoder.JSONDecodeError`
**Solution**: Check JSON syntax, ensure proper escaping of quotes and special characters

### Missing Dependencies
**Error**: `ModuleNotFoundError: No module named 'docx'`
**Solution**: Run `poetry install` to install all dependencies

### Semantic IR Not Extracted
**Issue**: Script reports 0 formulas/definitions but document has them
**Solution**:
1. Check document formatting (use proper heading styles, clear formulas)
2. Review extraction patterns - may need to add new patterns
3. Manually inspect the .docx file for non-standard formatting

### Test Failures After Enhancement
**Issue**: Tests fail after regenerating semantic IR
**Solution**:
1. Review the changes in the JSON file
2. Check if extraction improved (found more content)
3. Adjust test tolerance if extraction became more accurate
4. Manually verify extracted content is correct
