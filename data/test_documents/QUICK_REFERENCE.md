# Test Document Suite - Quick Reference

## Executive Summary

✓ **20 Word (.docx) documents** + **20 JSON metadata files** = **40 total files**  
✓ **158 total documented issues** across **10 categories**  
✓ Complexity: **6 low**, **8 medium**, **6 high**  
✓ Self-containment scores: **0.10** (worst) to **0.98** (perfect)

## Quick Selection Guide

### For 5-Minute Demo
```
1. doc_01 - Clean baseline (validate no false positives)
2. doc_08 - Internal contradictions (easy to see)
3. doc_05 - Market calendar issues (critical per ADR-018)
```

### For Smoke Testing
```
doc_01  - Nearly perfect (1 issue)
doc_08  - Inconsistent (6 issues)  
doc_11  - Perfect (0 issues)
doc_20  - Worst case (20 issues)
```

### For Comprehensive Testing
All 20 documents covering full spectrum

## Documents by Purpose

### Validate No False Positives
- **doc_01** - S&P Tech Index (1 low-severity issue)
- **doc_11** - Russell 2000 (0 issues) ⭐ Gold Standard
- **doc_19** - Bloomberg Agg Bond (2 low-severity issues)

### Test Critical Calendar Issues (ADR-018 Priority)
- **doc_05** - Global Multi-Asset (11 calendar issues)
- **doc_16** - Asia-Pacific Multi-Market (12 timezone issues) ⚠️

### Test Issue Detection Accuracy
- **doc_03** - Undefined Parameters (12 issues)
- **doc_04** - Incomplete Formulas (10 issues)
- **doc_14** - Multi-Issue Complex (15 issues across all categories)
- **doc_20** - Worst Case (20 severe issues) 🚨

### Test Compliance Gap Detection
- **doc_10** - Missing Risk Disclosures (5 compliance issues)
- **doc_20** - Crypto Strategy (non-compliant for investors)

### Test Consistency Validation
- **doc_08** - Quality Dividend Index (6 internal contradictions)

## Issue Category Map

| Category | Primary Documents | Total Issues |
|----------|------------------|--------------|
| `undefined_parameter` | 03, 06, 12, 17, 20 | 42 |
| `ambiguous_methodology` | 09, 12, 14, 16, 18 | 37 |
| `market_calendar` ⚠️ | 05, 16 | 20 |
| `data_source_unspecified` | 13, 14, 20 | 15 |
| `incomplete_formula` | 04, 12, 14 | 11 |
| `compliance_gap` | 10, 14, 20 | 10 |
| `missing_governance` | 07, 14 | 8 |
| `external_dependency` | 06, 14, 20 | 7 |
| `inconsistent_content` | 08 | 5 |
| `missing_reference` | 02 | 3 |

## Documents by Complexity

### Low Complexity (6 docs, avg 2.8 issues)
- doc_01 (1), doc_08 (6), doc_10 (5), doc_11 (0), doc_15 (3), doc_19 (2)

### Medium Complexity (8 docs, avg 8.2 issues)
- doc_02 (4), doc_03 (12), doc_04 (10), doc_06 (8), doc_07 (9), doc_09 (11), doc_13 (7), doc_17 (5)

### High Complexity (6 docs, avg 12.5 issues)
- doc_05 (11), doc_12 (8), doc_14 (15), doc_16 (12), doc_18 (9), doc_20 (20)

## Self-Containment Rankings

**Top 5 (Ready to Implement):**
1. doc_11: 0.98 - Russell 2000 EW Index
2. doc_01: 0.95 - S&P Tech Sector EW Index
3. doc_19: 0.93 - Bloomberg Agg Bond Replication
4. doc_15: 0.92 - U.S. Treasury Bond Index
5. doc_17: 0.65 - Dividend Aristocrats

**Bottom 5 (Major Issues):**
16. doc_09: 0.25 - ESG Enhanced Index
17. doc_16: 0.25 - Asia-Pacific Multi-Market ⚠️
18. doc_02: 0.20 - EM Dividend Growth
19. doc_14: 0.15 - Global Macro TAA
20. doc_20: 0.10 - Crypto Momentum 🚨

## Severity Distribution

| Severity | Count | % of Total |
|----------|-------|------------|
| Critical | 87 | 55.1% |
| High | 44 | 27.8% |
| Medium | 21 | 13.3% |
| Low | 6 | 3.8% |

## Expected AI Performance Targets

### Excellent Performance
- Clean docs (01, 11, 19): ≤2 false positives
- Worst case (20): ≥18 issues detected
- Calendar docs (05, 16): All critical issues flagged
- Self-containment: Within ±0.10 of metadata

### Acceptable Performance  
- False positive rate: ≤2 per clean document
- Detection rate: ≥80% of critical issues
- Severity accuracy: Within ±1 level of metadata

## File Locations

```
data/test_documents/
├── README.md                    # Full documentation
├── doc_01_clean.docx/.json
├── doc_02_missing_appendix.docx/.json
├── ... (20 total .docx files)
└── ... (20 total .json files)

scripts/
├── generate_test_documents.py       # Part 1 (docs 01-05)
├── generate_test_documents_part2.py # Part 2 (docs 06-10)
└── generate_test_documents_part3.py # Part 3 (docs 11-20)
```

## Related Documentation

- **[Full README](README.md)** - Comprehensive documentation
- **[ADR-018](../../docs/decisions/018-market-calendar-validation.md)** - Market Calendar Framework (CRITICAL)
- **[LLM Catalog](../../docs/architecture/LLM_PROMPT_CATALOG.md)** - AI enhancement recommendations
- **[IMPLEMENTATION_PLAN](../../docs/IMPLEMENTATION_PLAN.md)** - Phases 11-13 testing strategy

---

**Version**: 1.0 | **Status**: Complete | **Last Updated**: 2024-12-08  
**Commit**: 06985e5 | **Branch**: develop
