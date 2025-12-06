import pytest
from uuid import uuid4

from src.domain.exceptions.document_exceptions import (
    DocumentNotFound,
    InvalidDocumentFormat,
    DocumentAlreadyExists,
)
from src.domain.exceptions.analysis_exceptions import (
    AnalysisInProgress,
    AnalysisFailed,
    AnalysisNotStarted,
)
from src.domain.exceptions.feedback_exceptions import (
    FeedbackNotFound,
    ChangeAlreadyProcessed,
)
from src.domain.exceptions.policy_exceptions import (
    PolicyRepositoryNotFound,
    InvalidPolicy,
    PolicyAlreadyExists,
)


class TestDocumentExceptions:
    def test_document_not_found_has_document_id(self):
        doc_id = uuid4()
        exc = DocumentNotFound(document_id=doc_id)
        assert exc.document_id == doc_id
        assert str(doc_id) in str(exc)

    def test_invalid_document_format_has_format_info(self):
        exc = InvalidDocumentFormat(
            provided_format="image/png",
            supported_formats=["application/pdf", "docx"],
        )
        assert exc.provided_format == "image/png"
        assert "image/png" in str(exc)

    def test_document_already_exists(self):
        doc_id = uuid4()
        exc = DocumentAlreadyExists(document_id=doc_id)
        assert exc.document_id == doc_id


class TestAnalysisExceptions:
    def test_analysis_in_progress_has_document_id(self):
        doc_id = uuid4()
        exc = AnalysisInProgress(document_id=doc_id)
        assert exc.document_id == doc_id

    def test_analysis_failed_has_error_details(self):
        doc_id = uuid4()
        exc = AnalysisFailed(
            document_id=doc_id,
            error_message="API rate limit exceeded",
            error_code="RATE_LIMIT",
        )
        assert exc.document_id == doc_id
        assert exc.error_message == "API rate limit exceeded"
        assert exc.error_code == "RATE_LIMIT"

    def test_analysis_not_started(self):
        doc_id = uuid4()
        exc = AnalysisNotStarted(document_id=doc_id)
        assert exc.document_id == doc_id


class TestFeedbackExceptions:
    def test_feedback_not_found_has_feedback_id(self):
        feedback_id = uuid4()
        exc = FeedbackNotFound(feedback_id=feedback_id)
        assert exc.feedback_id == feedback_id

    def test_change_already_processed(self):
        feedback_id = uuid4()
        exc = ChangeAlreadyProcessed(
            feedback_id=feedback_id,
            current_status="ACCEPTED",
        )
        assert exc.feedback_id == feedback_id
        assert exc.current_status == "ACCEPTED"


class TestPolicyExceptions:
    def test_policy_repository_not_found(self):
        repo_id = uuid4()
        exc = PolicyRepositoryNotFound(repository_id=repo_id)
        assert exc.repository_id == repo_id

    def test_invalid_policy_has_reason(self):
        exc = InvalidPolicy(
            policy_name="Bad Policy",
            reason="Policy content is empty",
        )
        assert exc.policy_name == "Bad Policy"
        assert exc.reason == "Policy content is empty"

    def test_policy_already_exists(self):
        policy_name = "Risk Disclosure"
        exc = PolicyAlreadyExists(policy_name=policy_name)
        assert exc.policy_name == policy_name
