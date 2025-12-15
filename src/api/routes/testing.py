"""
API routes for testing and validation framework.

Provides endpoints for:
- Generating test cases from specifications
- Generating reference implementations
- Validating implementations
- Retrieving validation reports
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.dependencies import get_document_repository, get_current_user
from src.domain.aggregates.user import User
from src.domain.testing import (
    TestCaseGenerator,
    ReferenceImplementation,
    CrossValidator,
    TestCase,
    TestCategory,
    ValidationReport,
)


router = APIRouter(prefix="/testing", tags=["testing"])
logger = logging.getLogger(__name__)


# Schemas
class TestCaseRequest(BaseModel):
    """Request to generate test cases."""
    document_id: UUID
    formula_ids: Optional[List[str]] = Field(None, description="Specific formulas to test (None = all)")
    count_per_category: Optional[Dict[str, int]] = Field(
        None,
        description="Number of tests per category",
        example={"normal": 10, "boundary": 5, "edge": 3, "error": 2}
    )


class TestCaseResponse(BaseModel):
    """Response containing generated test cases."""
    document_id: UUID
    formula_id: str
    test_cases: List[Dict]
    total_tests: int


class ReferenceRequest(BaseModel):
    """Request to generate reference implementation."""
    document_id: UUID
    formula_id: str
    precision: Optional[int] = Field(None, description="Decimal places for rounding")
    include_validation: bool = Field(True, description="Include parameter validation")


class ReferenceResponse(BaseModel):
    """Response containing reference implementation code."""
    document_id: UUID
    formula_id: str
    function_name: str
    code: str


class ValidationRequest(BaseModel):
    """Request to validate an implementation."""
    document_id: UUID
    formula_id: str
    implementation_code: str
    test_case_ids: Optional[List[str]] = Field(None, description="Specific test cases to run (None = all)")
    tolerance: Optional[float] = Field(None, description="Custom tolerance for comparisons")


class ValidationResultResponse(BaseModel):
    """Response containing validation results."""
    report_id: str
    document_id: UUID
    formula_id: str
    success: bool
    pass_rate: float
    total_tests: int
    passed: int
    failed: int
    discrepancy_summary: Dict
    failed_tests: List[Dict]


@router.post("/test-cases", response_model=List[TestCaseResponse])
async def generate_test_cases(
    request: TestCaseRequest,
    current_user: User = Depends(get_current_user),
    document_repo = Depends(get_document_repository),
):
    """
    Generate test cases from document specifications.
    
    Creates comprehensive test suites covering normal, boundary, edge,
    and error scenarios for all formulas in the document.
    
    Args:
        request: Test case generation request
        current_user: Authenticated user
        document_repo: Document repository
        
    Returns:
        List of test cases grouped by formula
        
    Raises:
        404: Document not found or has no semantic IR
        403: User not authorized to access document
    """
    # Get document
    document = await document_repo.get_by_id(str(request.document_id))
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {request.document_id} not found"
        )
    
    # Check authorization (user can read document)
    # TODO: Add authorization check
    
    # Check document has semantic IR
    if not hasattr(document, 'semantic_ir') or not document.semantic_ir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {request.document_id} has no semantic IR"
        )
    
    document_ir = document.semantic_ir
    
    # Generate test cases
    generator = TestCaseGenerator()
    
    # Convert count_per_category to TestCategory enum keys
    count_per_category = None
    if request.count_per_category:
        count_per_category = {
            TestCategory(k): v for k, v in request.count_per_category.items()
        }
    
    test_suites = generator.generate_from_document(
        document_ir=document_ir,
        formulas_to_test=request.formula_ids,
    )
    
    # Format response
    responses = []
    for formula_id, test_cases in test_suites.items():
        responses.append(TestCaseResponse(
            document_id=request.document_id,
            formula_id=formula_id,
            test_cases=[
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
            total_tests=len(test_cases),
        ))
    
    logger.info(
        f"Generated {sum(r.total_tests for r in responses)} test cases "
        f"for document {request.document_id} by user {current_user.kerberos_id}"
    )
    
    return responses


@router.post("/reference", response_model=ReferenceResponse)
async def generate_reference_implementation(
    request: ReferenceRequest,
    current_user: User = Depends(get_current_user),
    document_repo = Depends(get_document_repository),
):
    """
    Generate reference implementation for a formula.
    
    Creates executable Python code that precisely matches the semantic
    specification, including precision handling and edge cases.
    
    Args:
        request: Reference generation request
        current_user: Authenticated user
        document_repo: Document repository
        
    Returns:
        Reference implementation code
        
    Raises:
        404: Document or formula not found
        403: User not authorized
        500: Code generation failed
    """
    # Get document
    document = await document_repo.get_by_id(str(request.document_id))
    if not document or not hasattr(document, 'semantic_ir') or not document.semantic_ir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {request.document_id} not found or has no semantic IR"
        )
    
    document_ir = document.semantic_ir
    
    # Find formula
    formula = document_ir.find_formula(request.formula_id)
    if not formula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Formula {request.formula_id} not found in document"
        )
    
    # Generate reference implementation
    ref_gen = ReferenceImplementation()
    
    try:
        code = ref_gen.generate_function_code(
            formula=formula,
            document_ir=document_ir,
            precision=request.precision,
            include_validation=request.include_validation,
        )
        
        function_name = ref_gen._get_function_name(formula)
        
        logger.info(
            f"Generated reference implementation for formula {request.formula_id} "
            f"by user {current_user.kerberos_id}"
        )
        
        return ReferenceResponse(
            document_id=request.document_id,
            formula_id=request.formula_id,
            function_name=function_name,
            code=code,
        )
    
    except Exception as e:
        logger.error(f"Failed to generate reference for {request.formula_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate reference implementation: {str(e)}"
        )


@router.post("/validate", response_model=ValidationResultResponse)
async def validate_implementation(
    request: ValidationRequest,
    current_user: User = Depends(get_current_user),
    document_repo = Depends(get_document_repository),
):
    """
    Validate an implementation against reference.
    
    Runs test cases and compares user implementation outputs against
    the reference implementation to detect discrepancies.
    
    Args:
        request: Validation request
        current_user: Authenticated user
        document_repo: Document repository
        
    Returns:
        Validation report with pass/fail status and discrepancies
        
    Raises:
        404: Document or formula not found
        400: Invalid implementation code
        500: Validation failed
    """
    # Get document and formula
    document = await document_repo.get_by_id(str(request.document_id))
    if not document or not hasattr(document, 'semantic_ir') or not document.semantic_ir:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {request.document_id} not found or has no semantic IR"
        )
    
    document_ir = document.semantic_ir
    formula = document_ir.find_formula(request.formula_id)
    if not formula:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Formula {request.formula_id} not found"
        )
    
    # Generate reference implementation
    ref_gen = ReferenceImplementation()
    try:
        reference_func = ref_gen.generate_reference(formula, document_ir)
    except Exception as e:
        logger.error(f"Failed to generate reference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate reference implementation: {str(e)}"
        )
    
    # Parse user implementation
    namespace = {}
    try:
        exec(request.implementation_code, namespace)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid implementation code: {str(e)}"
        )
    
    # Find the function in namespace
    impl_func = None
    for name, obj in namespace.items():
        if callable(obj) and not name.startswith('_'):
            impl_func = obj
            break
    
    if not impl_func:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No function found in implementation code"
        )
    
    # Generate test cases
    generator = TestCaseGenerator()
    test_cases = generator.generate_from_formula(formula, document_ir)
    
    # Filter to specific test cases if requested
    if request.test_case_ids:
        test_case_ids_set = set(request.test_case_ids)
        test_cases = [tc for tc in test_cases if str(tc.id) in test_case_ids_set]
    
    # Run validation
    validator = CrossValidator(default_tolerance=request.tolerance or 1e-10)
    
    try:
        report = validator.validate_implementation(
            implementation=impl_func,
            reference=reference_func,
            test_cases=test_cases,
            implementation_name="user_implementation",
            reference_name="reference",
            tolerance=request.tolerance,
        )
        
        logger.info(
            f"Validated implementation for formula {request.formula_id}: "
            f"{report.passed}/{report.total_tests} passed "
            f"by user {current_user.kerberos_id}"
        )
        
        return ValidationResultResponse(
            report_id=str(report.id),
            document_id=request.document_id,
            formula_id=request.formula_id,
            success=report.success,
            pass_rate=report.pass_rate,
            total_tests=report.total_tests,
            passed=report.passed,
            failed=report.failed,
            discrepancy_summary=report.discrepancy_summary,
            failed_tests=[
                {
                    "test_name": r.test_case.name,
                    "category": r.test_case.category.value,
                    "expected": r.test_case.expected_output,
                    "actual": r.actual_output,
                    "discrepancy": r.discrepancy,
                    "error": r.error_message,
                }
                for r in report.get_failed_tests()
            ],
        )
    
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )


@router.get("/reports/{report_id}")
async def get_validation_report(
    report_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a previously generated validation report.
    
    Args:
        report_id: Validation report ID
        current_user: Authenticated user
        
    Returns:
        Validation report
        
    Raises:
        404: Report not found
        403: User not authorized
    """
    # TODO: Implement report storage and retrieval
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Report retrieval not yet implemented"
    )
