#!/usr/bin/env python3
"""
Validation script for running specification-based testing.

Usage:
  python run_validation.py generate-tests --output tests/generated/
  python run_validation.py generate-references --output tests/reference/
  python run_validation.py validate --test-dir tests/generated/ --report validation-report.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from src.domain.testing import (
    TestCaseGenerator,
    ReferenceImplementation,
    CrossValidator,
    ValidationReport,
)
from src.domain.value_objects.semantic_ir import DocumentIR
from src.infrastructure.persistence.document_repository import DocumentRepository


def generate_test_cases(output_dir: Path, document_ids: List[str], verbose: bool = False):
    """Generate test cases from specifications."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generator = TestCaseGenerator()
    repo = DocumentRepository()
    
    total_tests = 0
    
    for doc_id in document_ids:
        if verbose:
            print(f"Generating tests for document {doc_id}...")
        
        # Load document IR
        document = repo.get_by_id(doc_id)
        if not document:
            print(f"Warning: Document {doc_id} not found", file=sys.stderr)
            continue
        
        # Assume document has semantic_ir attribute
        if not hasattr(document, 'semantic_ir') or not document.semantic_ir:
            print(f"Warning: Document {doc_id} has no semantic IR", file=sys.stderr)
            continue
        
        document_ir = document.semantic_ir
        
        # Generate test cases for all formulas
        test_suite = generator.generate_from_document(document_ir)
        
        # Save test cases
        for formula_id, test_cases in test_suite.items():
            output_file = output_dir / f"{doc_id}_{formula_id}_tests.json"
            
            with open(output_file, 'w') as f:
                json.dump(
                    {
                        "document_id": doc_id,
                        "formula_id": formula_id,
                        "test_cases": [
                            {
                                "id": str(tc.id),
                                "name": tc.name,
                                "category": tc.category.value,
                                "inputs": tc.inputs,
                                "expected_output": tc.expected_output,
                                "precision": tc.precision,
                                "tolerance": tc.tolerance,
                                "description": tc.description,
                                "metadata": tc.metadata,
                            }
                            for tc in test_cases
                        ],
                    },
                    f,
                    indent=2,
                    default=str,
                )
            
            total_tests += len(test_cases)
            
            if verbose:
                print(f"  Generated {len(test_cases)} tests for formula {formula_id}")
    
    print(f"✓ Generated {total_tests} test cases")


def generate_reference_implementations(output_dir: Path, document_ids: List[str], verbose: bool = False):
    """Generate reference implementations from specifications."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ref_gen = ReferenceImplementation()
    repo = DocumentRepository()
    
    total_impls = 0
    
    for doc_id in document_ids:
        if verbose:
            print(f"Generating reference implementations for document {doc_id}...")
        
        # Load document IR
        document = repo.get_by_id(doc_id)
        if not document or not hasattr(document, 'semantic_ir') or not document.semantic_ir:
            continue
        
        document_ir = document.semantic_ir
        
        # Generate reference for each formula
        for formula in document_ir.formulae:
            try:
                code = ref_gen.generate_function_code(formula, document_ir)
                
                output_file = output_dir / f"{doc_id}_{formula.id}_reference.py"
                with open(output_file, 'w') as f:
                    f.write(code)
                
                total_impls += 1
                
                if verbose:
                    print(f"  Generated reference for formula {formula.id}")
            
            except Exception as e:
                print(f"Warning: Failed to generate reference for {formula.id}: {e}", file=sys.stderr)
    
    print(f"✓ Generated {total_impls} reference implementations")


def run_validation(
    test_dir: Path,
    reference_dir: Path,
    implementations_dir: Path,
    report_path: Path,
    threshold: float,
    verbose: bool = False,
):
    """Run cross-validation between implementations and references."""
    validator = CrossValidator()
    
    # Load test cases
    test_files = list(test_dir.glob("*_tests.json"))
    if not test_files:
        print("Error: No test cases found", file=sys.stderr)
        sys.exit(1)
    
    all_reports = []
    
    for test_file in test_files:
        with open(test_file) as f:
            test_data = json.load(f)
        
        doc_id = test_data["document_id"]
        formula_id = test_data["formula_id"]
        
        if verbose:
            print(f"Validating {doc_id}/{formula_id}...")
        
        # Load reference implementation
        ref_file = reference_dir / f"{doc_id}_{formula_id}_reference.py"
        if not ref_file.exists():
            if verbose:
                print(f"  Warning: No reference found for {formula_id}")
            continue
        
        # Load and exec reference
        with open(ref_file) as f:
            ref_code = f.read()
        
        namespace = {}
        exec(ref_code, namespace)
        
        # Find the function (should be only one defined)
        ref_func = None
        for name, obj in namespace.items():
            if callable(obj) and not name.startswith('_'):
                ref_func = obj
                break
        
        if not ref_func:
            print(f"  Warning: No function found in reference for {formula_id}")
            continue
        
        # TODO: Load user implementation
        # For now, validate reference against itself (should pass)
        impl_func = ref_func
        
        # Convert test cases back to TestCase objects
        from src.domain.testing.test_case import TestCase, TestCategory
        test_cases = [
            TestCase(
                id=tc["id"],
                name=tc["name"],
                category=TestCategory(tc["category"]),
                inputs=tc["inputs"],
                expected_output=tc.get("expected_output"),
                precision=tc.get("precision"),
                tolerance=tc.get("tolerance"),
                description=tc["description"],
                metadata=tc["metadata"],
            )
            for tc in test_data["test_cases"]
        ]
        
        # Run validation
        report = validator.validate_implementation(
            implementation=impl_func,
            reference=ref_func,
            test_cases=test_cases,
            implementation_name=f"{doc_id}_{formula_id}",
            reference_name="reference",
        )
        
        all_reports.append(report)
        
        if verbose:
            print(f"  {report.passed}/{report.total_tests} passed ({report.pass_rate:.1f}%)")
    
    # Aggregate results
    total_tests = sum(r.total_tests for r in all_reports)
    total_passed = sum(r.passed for r in all_reports)
    total_failed = sum(r.failed for r in all_reports)
    
    aggregate_report = {
        "success": total_failed == 0,
        "total_tests": total_tests,
        "passed": total_passed,
        "failed": total_failed,
        "pass_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0,
        "reports": [r.to_dict() for r in all_reports],
        "threshold": threshold,
    }
    
    # Save report
    with open(report_path, 'w') as f:
        json.dump(aggregate_report, f, indent=2)
    
    print(f"\n{'✓' if aggregate_report['success'] else '✗'} Validation {'PASSED' if aggregate_report['success'] else 'FAILED'}")
    print(f"  Pass Rate: {aggregate_report['pass_rate']:.1f}% ({total_passed}/{total_tests})")
    print(f"  Report saved to {report_path}")
    
    if not aggregate_report['success']:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Run specification validation")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # generate-tests command
    gen_tests = subparsers.add_parser("generate-tests", help="Generate test cases")
    gen_tests.add_argument("--output", type=Path, required=True, help="Output directory")
    gen_tests.add_argument("--documents", nargs="+", help="Document IDs to process")
    gen_tests.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # generate-references command
    gen_refs = subparsers.add_parser("generate-references", help="Generate reference implementations")
    gen_refs.add_argument("--output", type=Path, required=True, help="Output directory")
    gen_refs.add_argument("--documents", nargs="+", help="Document IDs to process")
    gen_refs.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    # validate command
    validate = subparsers.add_parser("validate", help="Run validation")
    validate.add_argument("--test-dir", type=Path, required=True, help="Test cases directory")
    validate.add_argument("--reference-dir", type=Path, required=True, help="Reference implementations directory")
    validate.add_argument("--implementations", type=Path, help="User implementations directory")
    validate.add_argument("--report", type=Path, default=Path("validation-report.json"), help="Report output path")
    validate.add_argument("--threshold", type=float, default=100.0, help="Pass rate threshold")
    validate.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "generate-tests":
        document_ids = args.documents or []  # TODO: Get from database
        generate_test_cases(args.output, document_ids, args.verbose)
    
    elif args.command == "generate-references":
        document_ids = args.documents or []  # TODO: Get from database
        generate_reference_implementations(args.output, document_ids, args.verbose)
    
    elif args.command == "validate":
        implementations_dir = args.implementations or args.reference_dir
        run_validation(
            args.test_dir,
            args.reference_dir,
            implementations_dir,
            args.report,
            args.threshold,
            args.verbose,
        )


if __name__ == "__main__":
    main()
