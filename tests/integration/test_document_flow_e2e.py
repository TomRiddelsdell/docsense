"""End-to-end tests for document management flow.

Tests the complete lifecycle: upload, list, get, update, delete.
"""
import pytest
from uuid import UUID


class TestDocumentManagementE2E:
    """End-to-end tests for document CRUD operations."""

    @pytest.mark.asyncio
    async def test_upload_document(self, client, sample_markdown_file):
        """Test uploading a new document."""
        response = await client.post(
            "/api/v1/documents",
            files={"file": ("test_algorithm.md", sample_markdown_file, "text/markdown")},
            data={"title": "Test Trading Algorithm", "description": "E2E test document"},
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "title" in data
        assert data["status"] in ["uploaded", "pending", "draft", "converted"]
        UUID(data["id"])

    @pytest.mark.asyncio
    async def test_list_documents(self, client, sample_markdown_file):
        """Test listing documents."""
        await client.post(
            "/api/v1/documents",
            files={"file": ("list_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "List Test Doc"},
        )
        
        response = await client.get("/api/v1/documents")
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert isinstance(data["documents"], list)

    @pytest.mark.asyncio
    async def test_get_document_by_id(self, client, sample_markdown_file):
        """Test retrieving a specific document."""
        upload_response = await client.post(
            "/api/v1/documents",
            files={"file": ("get_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Get Test Doc"},
        )
        doc_id = upload_response.json()["id"]
        
        response = await client.get(f"/api/v1/documents/{doc_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert "title" in data

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, client):
        """Test 404 for non-existent document."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/documents/{fake_id}")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_document(self, client, sample_markdown_file):
        """Test updating a document."""
        upload_response = await client.post(
            "/api/v1/documents",
            files={"file": ("update_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Original Title"},
        )
        doc_id = upload_response.json()["id"]
        
        response = await client.patch(
            f"/api/v1/documents/{doc_id}",
            json={"title": "Updated Title", "description": "Updated description"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_document(self, client, sample_markdown_file):
        """Test deleting a document."""
        upload_response = await client.post(
            "/api/v1/documents",
            files={"file": ("delete_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Delete Test Doc"},
        )
        doc_id = upload_response.json()["id"]
        
        response = await client.delete(f"/api/v1/documents/{doc_id}")
        
        assert response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_get_document_content(self, client, sample_markdown_file):
        """Test retrieving document content."""
        upload_response = await client.post(
            "/api/v1/documents",
            files={"file": ("content_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Content Test Doc"},
        )
        doc_id = upload_response.json()["id"]
        
        response = await client.get(f"/api/v1/documents/{doc_id}/content")
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data or "markdown_content" in data

    @pytest.mark.asyncio
    async def test_document_pagination(self, client, sample_markdown_file):
        """Test document list pagination."""
        for i in range(3):
            await client.post(
                "/api/v1/documents",
                files={"file": (f"pagination_test_{i}.md", sample_markdown_file, "text/markdown")},
                data={"title": f"Pagination Test {i}"},
            )
        
        response = await client.get("/api/v1/documents", params={"page": 1, "per_page": 2})
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert len(data["documents"]) <= 2


class TestDocumentExportE2E:
    """End-to-end tests for document export functionality."""

    @pytest.mark.asyncio
    async def test_export_document_requires_analysis(self, client, sample_markdown_file):
        """Test that export fails for non-analyzed documents."""
        upload_response = await client.post(
            "/api/v1/documents",
            files={"file": ("export_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Export Test Doc"},
        )
        doc_id = upload_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/documents/{doc_id}/export",
            json={"format": "md"},
        )
        
        assert response.status_code == 400
