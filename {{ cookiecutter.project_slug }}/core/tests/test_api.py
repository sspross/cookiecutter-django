import pytest

from api_keys.services import mint
from api_keys.tests.factories import UserFactory

ME_URL = "/api/me"


@pytest.mark.django_db
class TestMeEndpoint:
    def test_session_auth_returns_username(self, client):
        user = UserFactory(username="alice")
        client.force_login(user)
        response = client.get(ME_URL)
        assert response.status_code == 200
        assert response.json() == {"username": "alice"}

    def test_bearer_auth_returns_username(self, client):
        user = UserFactory(username="bob")
        raw_token = mint(user, name="laptop-cli").raw_token
        response = client.get(
            ME_URL, HTTP_AUTHORIZATION=f"Bearer {raw_token}"
        )
        assert response.status_code == 200
        assert response.json() == {"username": "bob"}

    def test_anonymous_is_rejected(self, client):
        response = client.get(ME_URL)
        assert response.status_code == 401
