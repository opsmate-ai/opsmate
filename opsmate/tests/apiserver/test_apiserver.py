import pytest
from fastapi.testclient import TestClient
from opsmate.apiserver import app


class TestApiServer:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health(self, client):
        response = client.get("/api/v1/healthz")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_models(self, client):
        response = client.get("/api/v1/models")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) > 0
