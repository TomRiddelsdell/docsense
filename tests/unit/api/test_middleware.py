import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.middleware.request_id import RequestIdMiddleware


@pytest.fixture
def app_with_middleware():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    return app


@pytest.fixture
def client(app_with_middleware):
    return TestClient(app_with_middleware)


class TestRequestIdMiddleware:
    def test_adds_request_id_header_to_response(self, client):
        response = client.get("/test")
        assert "X-Request-ID" in response.headers

    def test_request_id_is_valid_uuid(self, client):
        import uuid
        response = client.get("/test")
        request_id = response.headers["X-Request-ID"]
        uuid.UUID(request_id)

    def test_uses_provided_request_id(self, client):
        custom_id = "custom-request-id-123"
        response = client.get("/test", headers={"X-Request-ID": custom_id})
        assert response.headers["X-Request-ID"] == custom_id
