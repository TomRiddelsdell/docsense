import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_check_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_check_returns_status_healthy(self, client):
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "healthy"
