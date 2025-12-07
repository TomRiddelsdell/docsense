import pytest
from uuid import uuid4
from datetime import datetime

from src.api.schemas.common import PaginationParams, PaginatedResponse, ErrorResponse
from src.api.schemas.documents import (
    DocumentUploadRequest,
    DocumentResponse,
    DocumentListResponse,
)
from src.api.schemas.analysis import (
    StartAnalysisRequest,
    AnalysisSessionResponse,
    AnalysisIssue,
    AnalysisProgress,
)
from src.api.schemas.feedback import (
    FeedbackItemResponse,
    RejectFeedbackRequest,
    FeedbackListResponse,
)
from src.api.schemas.policies import (
    PolicyRepositoryCreate,
    PolicyRepositoryResponse,
    PolicyCreate,
    PolicyResponse,
)
from src.api.schemas.audit import AuditEntry, AuditTrailResponse


class TestPaginationParams:
    def test_default_values(self):
        params = PaginationParams()
        assert params.page == 1
        assert params.per_page == 20

    def test_custom_values(self):
        params = PaginationParams(page=2, per_page=25)
        assert params.page == 2
        assert params.per_page == 25

    def test_offset_calculation(self):
        params = PaginationParams(page=3, per_page=20)
        assert params.offset == 40

    def test_limit_equals_per_page(self):
        params = PaginationParams(per_page=25)
        assert params.limit == 25


class TestErrorResponse:
    def test_error_response_creation(self):
        error = ErrorResponse(
            error="Not Found",
            message="Resource not found",
        )
        assert error.error == "Not Found"
        assert error.message == "Resource not found"

    def test_error_response_with_details(self):
        error = ErrorResponse(
            error="Validation Error",
            message="Invalid input",
            details={"field": "title", "issue": "required"},
        )
        assert error.details == {"field": "title", "issue": "required"}


class TestDocumentSchemas:
    def test_document_upload_request(self):
        request = DocumentUploadRequest(
            title="Test Document",
            description="A test document",
        )
        assert request.title == "Test Document"
        assert request.description == "A test document"

    def test_document_response(self):
        doc_id = uuid4()
        now = datetime.now()
        response = DocumentResponse(
            id=doc_id,
            title="Test Document",
            description="A test document",
            status="uploaded",
            version=1,
            created_at=now,
            updated_at=now,
        )
        assert response.id == doc_id
        assert response.title == "Test Document"
        assert response.version == 1

    def test_document_list_response(self):
        response = DocumentListResponse(
            documents=[],
            total=0,
            page=1,
            per_page=20,
        )
        assert response.total == 0
        assert response.documents == []


class TestAnalysisSchemas:
    def test_start_analysis_request(self):
        request = StartAnalysisRequest(
            model_provider="gemini",
            focus_areas=["compliance", "clarity"],
        )
        assert request.model_provider == "gemini"
        assert request.focus_areas == ["compliance", "clarity"]

    def test_analysis_session_response(self):
        doc_id = uuid4()
        response = AnalysisSessionResponse(
            document_id=doc_id,
            status="pending",
            issues_found=0,
        )
        assert response.document_id == doc_id
        assert response.status == "pending"

    def test_analysis_issue(self):
        issue = AnalysisIssue(
            id=uuid4(),
            category="compliance",
            severity="high",
            description="Missing risk disclosure",
            suggestion="Add risk factors section",
        )
        assert issue.category == "compliance"
        assert issue.severity == "high"


class TestFeedbackSchemas:
    def test_reject_feedback_request(self):
        request = RejectFeedbackRequest(
            reason="Not applicable to this document",
        )
        assert request.reason == "Not applicable to this document"

    def test_feedback_item_response(self):
        item = FeedbackItemResponse(
            id=uuid4(),
            document_id=uuid4(),
            status="pending",
            suggestion="Add more detail here",
            created_at=datetime.now(),
        )
        assert item.status == "pending"
        assert item.suggestion == "Add more detail here"

    def test_feedback_list_response(self):
        response = FeedbackListResponse(
            items=[],
            total=0,
            pending_count=0,
            accepted_count=0,
            rejected_count=0,
        )
        assert response.total == 0


class TestPolicySchemas:
    def test_policy_repository_create(self):
        request = PolicyRepositoryCreate(
            name="SEC Policies",
            description="SEC compliance policies",
        )
        assert request.name == "SEC Policies"

    def test_policy_create(self):
        request = PolicyCreate(
            name="Risk Disclosure",
            description="Risk disclosure requirements",
            requirement_type="must",
        )
        assert request.name == "Risk Disclosure"
        assert request.requirement_type == "must"

    def test_policy_repository_response(self):
        now = datetime.now()
        response = PolicyRepositoryResponse(
            id=uuid4(),
            name="SEC Policies",
            description="SEC compliance",
            policy_count=5,
            document_count=10,
            created_at=now,
            updated_at=now,
        )
        assert response.policy_count == 5

    def test_policy_response(self):
        now = datetime.now()
        response = PolicyResponse(
            id=uuid4(),
            repository_id=uuid4(),
            name="Risk Disclosure",
            description="Require risk disclosure",
            requirement_type="must",
            created_at=now,
            updated_at=now,
        )
        assert response.requirement_type == "must"


class TestAuditSchemas:
    def test_audit_entry(self):
        entry = AuditEntry(
            id=uuid4(),
            event_type="DocumentUploaded",
            document_id=uuid4(),
            user_id="user123",
            details={"filename": "test.pdf"},
            timestamp=datetime.now(),
        )
        assert entry.event_type == "DocumentUploaded"

    def test_audit_trail_response(self):
        response = AuditTrailResponse(
            entries=[],
            total=0,
            page=1,
            per_page=50,
        )
        assert response.total == 0
        assert response.entries == []
