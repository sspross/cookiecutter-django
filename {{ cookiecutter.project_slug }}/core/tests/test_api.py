import pytest

from api_keys.services import mint
from api_keys.tests.factories import UserFactory

ME_URL = "/api/me"


@pytest.mark.django_db
class TestMeEndpoint:
    def test_session_auth_returns_username(self, client):
        user = UserFactory.create(username="alice")
        client.force_login(user)
        response = client.get(ME_URL)
        assert response.status_code == 200
        assert response.json() == {"username": "alice"}

    def test_bearer_auth_returns_username(self, client):
        user = UserFactory.create(username="bob")
        raw_token = mint(user, name="laptop-cli").raw_token
        response = client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        assert response.status_code == 200
        assert response.json() == {"username": "bob"}

    def test_anonymous_is_rejected(self, client):
        response = client.get(ME_URL)
        assert response.status_code == 401

    def test_bearer_of_inactive_user_is_rejected(self, client):
        user = UserFactory.create(username="carol")
        result = mint(user, name="laptop-cli")
        user.is_active = False
        user.save(update_fields=["is_active"])

        response = client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {result.raw_token}")

        assert response.status_code == 401
        result.api_key.refresh_from_db()
        assert result.api_key.last_used_at is None

    def test_bearer_works_again_after_the_user_is_reactivated(self, client):
        user = UserFactory.create(username="dave")
        raw_token = mint(user, name="laptop-cli").raw_token
        user.is_active = False
        user.save(update_fields=["is_active"])
        assert (
            client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {raw_token}").status_code
            == 401
        )

        user.is_active = True
        user.save(update_fields=["is_active"])
        response = client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {raw_token}")

        assert response.status_code == 200
        assert response.json() == {"username": "dave"}


@pytest.mark.parametrize("url", ["/api/docs", "/api/openapi.json"])
def test_api_reference_is_readable_without_a_login(client, url):
    assert client.get(url).status_code == 200
