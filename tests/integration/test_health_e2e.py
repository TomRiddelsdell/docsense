"""End-to-end tests for health check endpoints."""
import pytest


class TestHealthCheckE2E:
    """End-to-end tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test the health check endpoint."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok"]

    @pytest.mark.asyncio
    async def test_health_check_response_time(self, client):
        """Test that health check responds quickly."""
        import time
        
        start = time.time()
        response = await client.get("/api/v1/health")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0


class TestAPIMetadata:
    """Tests for API metadata and documentation."""

    @pytest.mark.asyncio
    async def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is available."""
        response = await client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data
        assert "info" in data

    @pytest.mark.asyncio
    async def test_api_version_in_metadata(self, client):
        """Test that API version is present in OpenAPI metadata."""
        response = await client.get("/openapi.json")
        
        assert response.status_code == 200
        data = response.json()
        assert "info" in data
        assert "version" in data["info"]
        assert data["info"]["version"] == "1.0.0"
