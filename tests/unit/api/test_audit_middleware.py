"""Tests for AuditMiddleware helper methods."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4, UUID

from src.api.middleware.audit import AuditMiddleware
from src.infrastructure.audit.audit_logger import AuditLogger


@pytest.fixture
def middleware():
    """Create AuditMiddleware with mock logger."""
    mock_logger = AsyncMock(spec=AuditLogger)
    mock_logger.log_access = AsyncMock()
    app = MagicMock()
    return AuditMiddleware(app, mock_logger)


def test_extract_document_id_from_path(middleware):
    """Test extracting document ID from URL paths."""
    doc_id = str(uuid4())
    
    # Test various document paths
    paths = [
        f"/api/v1/documents/{doc_id}",
        f"/api/v1/documents/{doc_id}/content",
        f"/api/v1/documents/{doc_id}/share",
        f"/api/v1/documents/{doc_id}/analyze",
    ]
    
    for path in paths:
        result = middleware._extract_document_id(path)
        assert result == UUID(doc_id), f"Failed to extract from {path}"


def test_extract_document_id_returns_none_for_invalid_paths(middleware):
    """Test that extraction returns None for non-document paths."""
    paths = [
        "/api/v1/documents",
        "/api/v1/health",
        "/api/v1/policies/123",
        "/api/v1/documents/not-a-uuid",
    ]
    
    for path in paths:
        result = middleware._extract_document_id(path)
        assert result is None, f"Should not extract from {path}"


def test_determine_action_for_get_requests(middleware):
    """Test action determination for GET requests."""
    assert middleware._determine_action("GET", "/api/v1/documents/123") == "view"
    assert middleware._determine_action("GET", "/api/v1/documents/123/content") == "view"
    assert middleware._determine_action("GET", "/api/v1/documents/123/semantic-ir") == "view"
    assert middleware._determine_action("GET", "/api/v1/documents/123/download") == "download"


def test_determine_action_for_modification_requests(middleware):
    """Test action determination for modification requests."""
    assert middleware._determine_action("PATCH", "/api/v1/documents/123") == "edit"
    assert middleware._determine_action("PUT", "/api/v1/documents/123") == "edit"
    assert middleware._determine_action("DELETE", "/api/v1/documents/123") == "delete"


def test_determine_action_for_sharing_requests(middleware):
    """Test action determination for sharing requests."""
    assert middleware._determine_action("POST", "/api/v1/documents/123/share") == "share"
    assert middleware._determine_action("POST", "/api/v1/documents/123/make-private") == "share"


def test_determine_action_for_other_post_requests(middleware):
    """Test action determination for other POST requests."""
    assert middleware._determine_action("POST", "/api/v1/documents/123/export") == "export"
    assert middleware._determine_action("POST", "/api/v1/documents/123/analyze") == "analyze"


def test_determine_action_returns_none_for_unknown_paths(middleware):
    """Test that action determination returns None for unknown paths."""
    assert middleware._determine_action("GET", "/api/v1/documents") is None
    assert middleware._determine_action("GET", "/api/v1/health") is None
    assert middleware._determine_action("POST", "/api/v1/documents") is None
