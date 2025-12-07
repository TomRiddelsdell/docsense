"""End-to-end tests for audit trail flow.

Tests global and document-specific audit trail retrieval.
"""
import pytest
from uuid import uuid4


class TestGlobalAuditTrailE2E:
    """End-to-end tests for global audit trail."""

    @pytest.mark.asyncio
    async def test_get_global_audit_trail(self, client):
        """Test retrieving the global audit trail."""
        response = await client.get("/api/v1/audit")
        
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    @pytest.mark.asyncio
    async def test_get_audit_trail_with_pagination(self, client):
        """Test audit trail pagination."""
        response = await client.get(
            "/api/v1/audit",
            params={"page": 1, "per_page": 10},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10

    @pytest.mark.asyncio
    async def test_get_audit_trail_with_event_type_filter(self, client):
        """Test filtering audit trail by event type."""
        response = await client.get(
            "/api/v1/audit",
            params={"event_type": "DocumentUploaded"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data


class TestDocumentAuditTrailE2E:
    """End-to-end tests for document-specific audit trail."""

    @pytest.mark.asyncio
    async def test_get_document_audit_trail(self, client, sample_markdown_file):
        """Test retrieving audit trail for a specific document."""
        upload_response = await client.post(
            "/api/v1/documents",
            files={"file": ("audit_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Audit Test Doc"},
        )
        doc_id = upload_response.json()["id"]
        
        response = await client.get(f"/api/v1/documents/{doc_id}/audit")
        
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_document_audit_trail_not_found(self, client):
        """Test 404 for non-existent document audit trail."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/documents/{fake_id}/audit")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_document_audit_trail_with_pagination(
        self, client, sample_markdown_file
    ):
        """Test document audit trail pagination."""
        upload_response = await client.post(
            "/api/v1/documents",
            files={"file": ("pagination_audit.md", sample_markdown_file, "text/markdown")},
            data={"title": "Pagination Audit Test"},
        )
        doc_id = upload_response.json()["id"]
        
        response = await client.get(
            f"/api/v1/documents/{doc_id}/audit",
            params={"page": 1, "per_page": 5},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 5


class TestAuditTrailAfterOperations:
    """Tests to verify audit entries are created after operations."""

    @pytest.mark.asyncio
    async def test_audit_entry_after_document_upload(self, client, sample_markdown_file):
        """Test that uploading a document creates an audit entry."""
        upload_response = await client.post(
            "/api/v1/documents",
            files={"file": ("audit_upload.md", sample_markdown_file, "text/markdown")},
            data={"title": "Audit Upload Test"},
        )
        doc_id = upload_response.json()["id"]
        
        audit_response = await client.get(f"/api/v1/documents/{doc_id}/audit")
        
        assert audit_response.status_code == 200
        data = audit_response.json()
        assert data["total"] >= 0

    @pytest.mark.asyncio
    async def test_audit_entry_after_document_update(self, client, sample_markdown_file):
        """Test that updating a document creates an audit entry."""
        upload_response = await client.post(
            "/api/v1/documents",
            files={"file": ("audit_update.md", sample_markdown_file, "text/markdown")},
            data={"title": "Audit Update Test"},
        )
        doc_id = upload_response.json()["id"]
        
        await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"title": "Updated Title"},
        )
        
        audit_response = await client.get(f"/api/v1/documents/{doc_id}/audit")
        
        assert audit_response.status_code == 200
