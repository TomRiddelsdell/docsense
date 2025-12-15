#!/usr/bin/env python3
"""
Check validation report and exit with appropriate status code.

Usage:
  python check_validation.py --report validation-report.json --threshold 100 --fail-on-error
"""

import argparse
import json
import sys
from pathlib import Path


def check_validation_report(report_path: Path, threshold: float, fail_on_error: bool):
    """Check validation report and exit with status code."""
    
    if not report_path.exists():
        print(f"Error: Report file not found: {report_path}", file=sys.stderr)
        sys.exit(1)
    
    with open(report_path) as f:
        report = json.load(f)
    
    pass_rate = report.get("pass_rate", 0.0)
    success = report.get("success", False)
    total_tests = report.get("total_tests", 0)
    passed = report.get("passed", 0)
    failed = report.get("failed", 0)
    
    # Print summary
    print("=" * 60)
    print("SPECIFICATION VALIDATION REPORT")
    print("=" * 60)
    print()
    print(f"Status: {'✓ PASSED' if success else '✗ FAILED'}")
    print(f"Pass Rate: {pass_rate:.1f}% ({passed}/{total_tests})")
    print(f"Threshold: {threshold}%")
    print()
    
    # Show failed tests if any
    if failed > 0:
        print(f"Failed Tests: {failed}")
        print()
        
        failed_tests = report.get("failed_tests", [])
        for i, test in enumerate(failed_tests[:10], 1):
            print(f"{i}. {test.get('test_name', 'Unknown')}")
            print(f"   Expected: {test.get('expected')}")
            print(f"   Actual: {test.get('actual')}")
            if test.get('discrepancy'):
                print(f"   Discrepancy: {test['discrepancy']}")
            if test.get('error'):
                print(f"   Error: {test['error']}")
            print()
        
        if len(failed_tests) > 10:
            print(f"... and {len(failed_tests) - 10} more failed tests")
            print()
    
    # Show discrepancy summary if available
    if "discrepancy_summary" in report:
        ds = report["discrepancy_summary"]
        print("Discrepancy Summary:")
        print(f"  Numeric Tests: {ds.get('numeric_tests', 0)}")
        print(f"  Max Discrepancy: {ds.get('max_discrepancy', 'N/A')}")
        print(f"  Mean Discrepancy: {ds.get('mean_discrepancy', 'N/A')}")
        print(f"  Median Discrepancy: {ds.get('median_discrepancy', 'N/A')}")
        print(f"  Tests with Discrepancy: {ds.get('tests_with_discrepancy', 0)}")
        print()
    
    print("=" * 60)
    
    # Determine exit code
    if pass_rate < threshold:
        print(f"\n✗ Validation FAILED: Pass rate {pass_rate:.1f}% below threshold {threshold}%")
        if fail_on_error:
            sys.exit(1)
    
    if not success:
        print(f"\n✗ Validation FAILED: {failed} test(s) failed")
        if fail_on_error:
            sys.exit(1)
    
    print(f"\n✓ Validation PASSED: All tests passed successfully")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Check validation report")
    parser.add_argument("--report", type=Path, required=True, help="Validation report file")
    parser.add_argument("--threshold", type=float, default=100.0, help="Pass rate threshold (%)")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit with error code if validation fails")
    
    args = parser.parse_args()
    
    check_validation_report(args.report, args.threshold, args.fail_on_error)


if __name__ == "__main__":
    main()
