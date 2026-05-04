# Unit tests for the project-wide Ninja API endpoints (`/api/health`,
# `/api/config`).

import pytest


@pytest.mark.django_db
class TestHealth:
    def test_returns_ok(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.django_db
class TestConfig:
    def test_returns_runtime_config(self, client):
        response = client.get("/api/config")
        assert response.status_code == 200
        body = response.json()
        assert "project_name" in body
        assert "debug" in body

    def test_sets_csrf_cookie(self, client):
        response = client.get("/api/config")
        assert "csrftoken" in response.cookies
