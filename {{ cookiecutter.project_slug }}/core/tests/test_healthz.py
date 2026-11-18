from unittest import mock

import pytest
import redis

from core.tests.fresh_settings import freshly_imported_production_settings

HEALTHZ_URL = "/healthz"


@pytest.mark.django_db
class TestHealthz:
    def test_reports_ok_when_database_and_redis_respond(self, client):
        with mock.patch.object(redis.Redis, "ping", return_value=True):
            response = client.get(HEALTHZ_URL)
        assert response.status_code == 200
        assert response.json() == {"database": "ok", "redis": "ok"}

    def test_reports_503_when_redis_ping_fails(self, client):
        with mock.patch.object(
            redis.Redis, "ping", side_effect=redis.ConnectionError("refused")
        ):
            response = client.get(HEALTHZ_URL)
        assert response.status_code == 503
        assert response.json() == {"database": "ok", "redis": "error"}

    def test_never_sets_a_cookie(self, client):
        with mock.patch.object(redis.Redis, "ping", return_value=True):
            response = client.get(HEALTHZ_URL)
        assert "Set-Cookie" not in response.headers
        assert response.cookies == {}

    def test_is_not_redirected_to_https(self, client, settings):
        exempt = freshly_imported_production_settings(["SECURE_REDIRECT_EXEMPT"])
        settings.SECURE_SSL_REDIRECT = True
        settings.SECURE_REDIRECT_EXEMPT = exempt["SECURE_REDIRECT_EXEMPT"]

        with mock.patch.object(redis.Redis, "ping", return_value=True):
            probe = client.get(HEALTHZ_URL)
        page = client.get("/accounts/login/")

        assert probe.status_code == 200
        assert page.status_code == 301
