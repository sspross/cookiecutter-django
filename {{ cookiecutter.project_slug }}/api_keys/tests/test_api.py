"""HTTP-level tests for ``/api/api-keys/*``.

These exercise the ninja router as a thin adapter over
``api_keys.services``. They assert on observable behaviour — status
codes, response JSON, persisted state — and never on which service
helper was called or in what order. Service-level cases live in
``test_services.py``.
"""

from __future__ import annotations

import pytest

from api_keys import services as api_keys
from api_keys.models import UserApiKey
from api_keys.tests.factories import UserFactory


@pytest.mark.django_db
class TestListApiKeys:
    def test_lists_only_own_keys_newest_first(self, client):
        alice = UserFactory(username="alice")
        bob = UserFactory(username="bob")
        api_keys.mint(bob, name="bob-key")
        alice_old = api_keys.mint(alice, name="alice-old").api_key
        alice_new = api_keys.mint(alice, name="alice-new").api_key
        client.force_login(alice)

        response = client.get("/api/api-keys/")

        assert response.status_code == 200
        rows = response.json()
        assert [r["name"] for r in rows] == ["alice-new", "alice-old"]
        assert {r["id"] for r in rows} == {alice_new.id, alice_old.id}

    def test_includes_revoked_keys(self, client):
        user = UserFactory()
        result = api_keys.mint(user, name="rotated")
        api_keys.revoke(result.api_key)
        client.force_login(user)

        response = client.get("/api/api-keys/")

        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 1
        assert rows[0]["revoked_at"] is not None

    def test_does_not_leak_hash(self, client):
        user = UserFactory()
        api_keys.mint(user, name="ci")
        client.force_login(user)

        response = client.get("/api/api-keys/")

        assert response.status_code == 200
        for row in response.json():
            assert "hash" not in row

    def test_requires_session_auth(self, client):
        response = client.get("/api/api-keys/")
        assert response.status_code == 401

    def test_rejects_bearer_auth(self, client):
        """Per-router override: bearer tokens cannot list keys, even when
        valid. Prevents a leaked token from enumerating siblings."""
        user = UserFactory()
        result = api_keys.mint(user, name="ci")

        response = client.get(
            "/api/api-keys/",
            HTTP_AUTHORIZATION=f"Bearer {result.raw_token}",
        )

        assert response.status_code == 401


@pytest.mark.django_db
class TestCreateApiKey:
    def test_mint_returns_201_with_raw_token_and_api_key(self, client):
        user = UserFactory()
        client.force_login(user)

        response = client.post(
            "/api/api-keys/",
            data={"name": "ci"},
            content_type="application/json",
        )

        assert response.status_code == 201
        body = response.json()
        assert body["raw_token"].startswith(api_keys.TOKEN_PREFIX)
        assert body["api_key"]["name"] == "ci"
        assert body["api_key"]["prefix"] == body["raw_token"][:12]
        assert body["api_key"]["revoked_at"] is None
        # The persisted row owns the same id and never the raw token.
        api_key = UserApiKey.objects.get(pk=body["api_key"]["id"])
        assert api_key.user == user

    def test_subsequent_list_does_not_return_raw_token(self, client):
        user = UserFactory()
        client.force_login(user)
        client.post(
            "/api/api-keys/",
            data={"name": "ci"},
            content_type="application/json",
        )

        response = client.get("/api/api-keys/")

        assert response.status_code == 200
        for row in response.json():
            assert "raw_token" not in row
            assert "hash" not in row

    def test_requires_session_auth(self, client):
        response = client.post(
            "/api/api-keys/",
            data={"name": "ci"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_rejects_bearer_auth(self, client):
        """Bearer auth cannot mint a key, preventing token-based escalation."""
        user = UserFactory()
        result = api_keys.mint(user, name="ci")

        response = client.post(
            "/api/api-keys/",
            data={"name": "evil"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {result.raw_token}",
        )

        assert response.status_code == 401
        # Only the seed key exists.
        assert UserApiKey.objects.filter(user=user).count() == 1


@pytest.mark.django_db
class TestRevokeApiKey:
    def test_revoke_flips_revoked_at(self, client):
        user = UserFactory()
        result = api_keys.mint(user, name="ci")
        client.force_login(user)

        response = client.post(f"/api/api-keys/{result.api_key.id}/revoke/")

        assert response.status_code == 200
        body = response.json()
        assert body["revoked_at"] is not None
        result.api_key.refresh_from_db()
        assert result.api_key.revoked_at is not None

    def test_revoke_is_idempotent(self, client):
        user = UserFactory()
        result = api_keys.mint(user, name="ci")
        client.force_login(user)

        first = client.post(f"/api/api-keys/{result.api_key.id}/revoke/")
        result.api_key.refresh_from_db()
        first_revoked_at = result.api_key.revoked_at

        second = client.post(f"/api/api-keys/{result.api_key.id}/revoke/")

        assert first.status_code == 200
        assert second.status_code == 200
        result.api_key.refresh_from_db()
        # Idempotent: second call does not change the revocation timestamp.
        assert result.api_key.revoked_at == first_revoked_at

    def test_cross_user_revoke_returns_404(self, client):
        """Returning 404 (not 403) avoids existence disclosure of other
        users' keys."""
        alice = UserFactory(username="alice")
        bob = UserFactory(username="bob")
        bob_key = api_keys.mint(bob, name="bob-key").api_key
        client.force_login(alice)

        response = client.post(f"/api/api-keys/{bob_key.id}/revoke/")

        assert response.status_code == 404
        bob_key.refresh_from_db()
        assert bob_key.revoked_at is None

    def test_revoke_unknown_id_returns_404(self, client):
        user = UserFactory()
        client.force_login(user)

        response = client.post("/api/api-keys/999999/revoke/")

        assert response.status_code == 404

    def test_requires_session_auth(self, client):
        user = UserFactory()
        result = api_keys.mint(user, name="ci")

        response = client.post(f"/api/api-keys/{result.api_key.id}/revoke/")

        assert response.status_code == 401

    def test_rejects_bearer_auth(self, client):
        user = UserFactory()
        result = api_keys.mint(user, name="ci")

        response = client.post(
            f"/api/api-keys/{result.api_key.id}/revoke/",
            HTTP_AUTHORIZATION=f"Bearer {result.raw_token}",
        )

        assert response.status_code == 401
        result.api_key.refresh_from_db()
        assert result.api_key.revoked_at is None


@pytest.mark.django_db
class TestVerifyAfterRevokeViaEndpoint:
    """No regression: revoking via the endpoint must invalidate the bearer
    token for the headless data API."""

    def test_revoked_via_endpoint_token_is_rejected_by_verify(self, client):
        user = UserFactory()
        result = api_keys.mint(user, name="ci")
        client.force_login(user)

        client.post(f"/api/api-keys/{result.api_key.id}/revoke/")

        assert api_keys.verify(result.raw_token) is None
