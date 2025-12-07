"""End-to-end tests for policy repository management flow.

Tests policy repository CRUD and policy management.
"""
import pytest
from uuid import UUID, uuid4


class TestPolicyRepositoryE2E:
    """End-to-end tests for policy repository CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_policy_repository(self, client, sample_policy_data):
        """Test creating a new policy repository."""
        response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_policy_data["name"]
        assert data["description"] == sample_policy_data["description"]
        UUID(data["id"])

    @pytest.mark.asyncio
    async def test_list_policy_repositories(self, client, sample_policy_data):
        """Test listing policy repositories."""
        await client.post("/api/v1/policy-repositories", json=sample_policy_data)
        
        response = await client.get("/api/v1/policy-repositories")
        
        assert response.status_code == 200
        data = response.json()
        assert "repositories" in data
        assert isinstance(data["repositories"], list)

    @pytest.mark.asyncio
    async def test_get_policy_repository_by_id(self, client, sample_policy_data):
        """Test retrieving a specific policy repository."""
        create_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/policy-repositories/{repo_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == repo_id
        assert data["name"] == sample_policy_data["name"]

    @pytest.mark.asyncio
    async def test_get_policy_repository_not_found(self, client):
        """Test 404 for non-existent policy repository."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/policy-repositories/{fake_id}")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_policy_repository(self, client, sample_policy_data):
        """Test updating a policy repository."""
        create_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = create_response.json()["id"]
        
        response = await client.patch(
            f"/api/v1/policy-repositories/{repo_id}",
            json={"name": "Updated Repository Name"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Repository Name"

    @pytest.mark.asyncio
    async def test_delete_policy_repository(self, client, sample_policy_data):
        """Test deleting a policy repository."""
        create_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = create_response.json()["id"]
        
        response = await client.delete(f"/api/v1/policy-repositories/{repo_id}")
        
        assert response.status_code == 204
        
        get_response = await client.get(f"/api/v1/policy-repositories/{repo_id}")
        assert get_response.status_code == 404


class TestPolicyManagementE2E:
    """End-to-end tests for managing policies within a repository."""

    @pytest.mark.asyncio
    async def test_add_policy_to_repository(self, client, sample_policy_data, sample_policy_rule):
        """Test adding a policy to a repository."""
        create_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = create_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/policy-repositories/{repo_id}/policies",
            json=sample_policy_rule,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_policy_rule["name"]

    @pytest.mark.asyncio
    async def test_list_policies_in_repository(self, client, sample_policy_data, sample_policy_rule):
        """Test listing policies in a repository."""
        create_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = create_response.json()["id"]
        
        await client.post(
            f"/api/v1/policy-repositories/{repo_id}/policies",
            json=sample_policy_rule,
        )
        
        response = await client.get(f"/api/v1/policy-repositories/{repo_id}/policies")
        
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert len(data["policies"]) >= 1

    @pytest.mark.asyncio
    async def test_get_policy_by_id(self, client, sample_policy_data, sample_policy_rule):
        """Test retrieving a specific policy."""
        create_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = create_response.json()["id"]
        
        policy_response = await client.post(
            f"/api/v1/policy-repositories/{repo_id}/policies",
            json=sample_policy_rule,
        )
        policy_id = policy_response.json()["id"]
        
        response = await client.get(
            f"/api/v1/policy-repositories/{repo_id}/policies/{policy_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == policy_id

    @pytest.mark.asyncio
    async def test_delete_policy(self, client, sample_policy_data, sample_policy_rule):
        """Test removing a policy from a repository."""
        create_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = create_response.json()["id"]
        
        policy_response = await client.post(
            f"/api/v1/policy-repositories/{repo_id}/policies",
            json=sample_policy_rule,
        )
        policy_id = policy_response.json()["id"]
        
        response = await client.delete(
            f"/api/v1/policy-repositories/{repo_id}/policies/{policy_id}"
        )
        
        assert response.status_code == 204


class TestDocumentPolicyAssignmentE2E:
    """End-to-end tests for assigning documents to policy repositories."""

    @pytest.mark.asyncio
    async def test_assign_document_to_policy_repository(
        self, client, sample_markdown_file, sample_policy_data
    ):
        """Test assigning a document to a policy repository."""
        doc_response = await client.post(
            "/api/v1/documents",
            files={"file": ("assign_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Assignment Test Doc"},
        )
        doc_id = doc_response.json()["id"]
        
        repo_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = repo_response.json()["id"]
        
        response = await client.put(
            f"/api/v1/documents/{doc_id}/policy-repository",
            json={"policy_repository_id": repo_id},
        )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_remove_document_policy_assignment(
        self, client, sample_markdown_file, sample_policy_data
    ):
        """Test removing document policy assignment."""
        doc_response = await client.post(
            "/api/v1/documents",
            files={"file": ("unassign_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Unassign Test Doc"},
        )
        doc_id = doc_response.json()["id"]
        
        repo_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = repo_response.json()["id"]
        
        await client.put(
            f"/api/v1/documents/{doc_id}/policy-repository",
            json={"policy_repository_id": repo_id},
        )
        
        response = await client.delete(f"/api/v1/documents/{doc_id}/policy-repository")
        
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_get_document_compliance_status(
        self, client, sample_markdown_file, sample_policy_data
    ):
        """Test checking document compliance status."""
        doc_response = await client.post(
            "/api/v1/documents",
            files={"file": ("compliance_test.md", sample_markdown_file, "text/markdown")},
            data={"title": "Compliance Test Doc"},
        )
        doc_id = doc_response.json()["id"]
        
        repo_response = await client.post(
            "/api/v1/policy-repositories",
            json=sample_policy_data,
        )
        repo_id = repo_response.json()["id"]
        
        await client.put(
            f"/api/v1/documents/{doc_id}/policy-repository",
            json={"policy_repository_id": repo_id},
        )
        
        response = await client.get(f"/api/v1/documents/{doc_id}/compliance")
        
        assert response.status_code == 200
        data = response.json()
        assert "compliance_status" in data or "status" in data
