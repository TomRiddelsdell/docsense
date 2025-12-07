"""End-to-end tests for feedback management flow.

Tests retrieving, accepting, and rejecting feedback.
"""
import pytest
from uuid import uuid4


class TestFeedbackE2E:
    """End-to-end tests for feedback operations."""

    @pytest.fixture
    async def document_with_policy(self, client, sample_markdown_file, sample_policy_data):
        """Create a document assigned to a policy repository."""
        repo_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = repo_response.json()["id"]
        
        doc_response = await client.post(
            "/api/v1/documents",
            files={"file": ("feedback_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Feedback Test Doc"},
        )
        doc_id = doc_response.json()["id"]
        
        await client.put(
            f"/api/v1/documents/{doc_id}/policy-repository",
            json={"policy_repository_id": repo_id},
        )
        
        return {"doc_id": doc_id, "repo_id": repo_id}

    @pytest.mark.asyncio
    async def test_get_document_feedback(self, client, document_with_policy):
        """Test retrieving feedback for a document."""
        doc_id = document_with_policy["doc_id"]
        
        response = await client.get(f"/api/v1/documents/{doc_id}/feedback")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "pending_count" in data
        assert "accepted_count" in data
        assert "rejected_count" in data

    @pytest.mark.asyncio
    async def test_get_feedback_not_found(self, client):
        """Test 404 for non-existent document feedback."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/documents/{fake_id}/feedback")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_feedback_filtered_by_status(self, client, document_with_policy):
        """Test filtering feedback by status."""
        doc_id = document_with_policy["doc_id"]
        
        response = await client.get(
            f"/api/v1/documents/{doc_id}/feedback",
            params={"status": "pending"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestFeedbackActionsE2E:
    """End-to-end tests for feedback accept/reject actions.
    
    Note: These tests require feedback items to exist, which normally
    happens after running analysis. For isolated testing, we verify
    the API endpoints respond correctly.
    """

    @pytest.fixture
    async def document_with_policy(self, client, sample_markdown_file, sample_policy_data):
        """Create a document assigned to a policy repository."""
        repo_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = repo_response.json()["id"]
        
        doc_response = await client.post(
            "/api/v1/documents",
            files={"file": ("action_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Feedback Action Test Doc"},
        )
        doc_id = doc_response.json()["id"]
        
        await client.put(
            f"/api/v1/documents/{doc_id}/policy-repository",
            json={"policy_repository_id": repo_id},
        )
        
        return {"doc_id": doc_id, "repo_id": repo_id}

    @pytest.mark.asyncio
    async def test_accept_feedback_not_found(self, client, document_with_policy):
        """Test accepting non-existent feedback returns 404."""
        doc_id = document_with_policy["doc_id"]
        fake_feedback_id = "00000000-0000-0000-0000-000000000000"
        
        response = await client.post(
            f"/api/v1/documents/{doc_id}/feedback/{fake_feedback_id}/accept"
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_feedback_not_found(self, client, document_with_policy):
        """Test rejecting non-existent feedback returns 404."""
        doc_id = document_with_policy["doc_id"]
        fake_feedback_id = "00000000-0000-0000-0000-000000000000"
        
        response = await client.post(
            f"/api/v1/documents/{doc_id}/feedback/{fake_feedback_id}/reject",
            json={"reason": "Test rejection reason"},
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_specific_feedback_not_found(self, client, document_with_policy):
        """Test getting non-existent specific feedback returns 404."""
        doc_id = document_with_policy["doc_id"]
        fake_feedback_id = "00000000-0000-0000-0000-000000000000"
        
        response = await client.get(
            f"/api/v1/documents/{doc_id}/feedback/{fake_feedback_id}"
        )
        
        assert response.status_code == 404
