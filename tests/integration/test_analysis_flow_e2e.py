"""End-to-end tests for document analysis flow.

Tests starting analysis, checking status, and cancellation.
"""
import pytest
import pytest_asyncio
from uuid import uuid4


class TestDocumentAnalysisE2E:
    """End-to-end tests for document analysis operations."""

    @pytest_asyncio.fixture
    async def document_with_policy(self, client, sample_markdown_file, sample_policy_data):
        """Create a document assigned to a policy repository."""
        repo_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = repo_response.json()["id"]
        
        doc_response = await client.post(
            "/api/v1/documents",
            files={"file": ("analysis_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Analysis Test Doc"},
        )
        doc_id = doc_response.json()["id"]
        
        await client.put(
            f"/api/v1/documents/{doc_id}/policy-repository",
            json={"policy_repository_id": repo_id},
        )
        
        return {"doc_id": doc_id, "repo_id": repo_id}

    @pytest.mark.asyncio
    async def test_start_analysis(self, client, document_with_policy):
        """Test starting document analysis."""
        doc_id = document_with_policy["doc_id"]
        
        response = await client.post(
            f"/api/v1/documents/{doc_id}/analyze",
            json={"model_provider": "gemini"},
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["document_id"] == doc_id
        assert "status" in data

    @pytest.mark.asyncio
    async def test_start_analysis_without_policy_fails(self, client, sample_markdown_file):
        """Test that analysis requires a policy repository assignment."""
        doc_response = await client.post(
            "/api/v1/documents",
            files={"file": ("no_policy_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "No Policy Test Doc"},
        )
        doc_id = doc_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/documents/{doc_id}/analyze",
            json={"model_provider": "gemini"},
        )
        
        assert response.status_code == 400
        assert "policy" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_analysis_status(self, client, document_with_policy):
        """Test getting analysis status."""
        doc_id = document_with_policy["doc_id"]
        
        response = await client.get(f"/api/v1/documents/{doc_id}/analysis")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_analysis_status_not_found(self, client):
        """Test 404 for non-existent document analysis status."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/documents/{fake_id}/analysis")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_analysis(self, client, document_with_policy):
        """Test canceling an analysis."""
        doc_id = document_with_policy["doc_id"]
        
        await client.post(
            f"/api/v1/documents/{doc_id}/analyze",
            json={"model_provider": "gemini"},
        )
        
        response = await client.delete(f"/api/v1/documents/{doc_id}/analysis")
        
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_get_analysis_logs(self, client, document_with_policy):
        """Test retrieving analysis logs."""
        doc_id = document_with_policy["doc_id"]
        
        response = await client.get(f"/api/v1/documents/{doc_id}/analysis-logs")
        
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert "entries" in data


class TestAnalysisWithDifferentProviders:
    """Tests for analysis with different AI model providers."""

    @pytest_asyncio.fixture
    async def document_with_policy(self, client, sample_markdown_file, sample_policy_data):
        """Create a document assigned to a policy repository."""
        repo_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = repo_response.json()["id"]
        
        doc_response = await client.post(
            "/api/v1/documents",
            files={"file": ("provider_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Provider Test Doc"},
        )
        doc_id = doc_response.json()["id"]
        
        await client.put(
            f"/api/v1/documents/{doc_id}/policy-repository",
            json={"policy_repository_id": repo_id},
        )
        
        return {"doc_id": doc_id, "repo_id": repo_id}

    @pytest.mark.asyncio
    async def test_start_analysis_with_gemini(self, client, document_with_policy):
        """Test starting analysis with Gemini provider."""
        doc_id = document_with_policy["doc_id"]
        
        response = await client.post(
            f"/api/v1/documents/{doc_id}/analyze",
            json={"model_provider": "gemini"},
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data.get("model_provider") == "gemini"

    @pytest.mark.asyncio
    async def test_start_analysis_default_provider(self, client, document_with_policy):
        """Test starting analysis with default provider."""
        doc_id = document_with_policy["doc_id"]
        
        response = await client.post(
            f"/api/v1/documents/{doc_id}/analyze",
        )
        
        assert response.status_code == 202
