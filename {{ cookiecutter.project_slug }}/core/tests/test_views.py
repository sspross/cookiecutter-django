import pytest
from django.urls import reverse

from api_keys.tests.factories import UserFactory


@pytest.mark.django_db
class TestHomeView:
    def test_home_redirects_anonymous(self, client):
        url = reverse("home")
        response = client.get(url)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_home_renders_for_authenticated_user(self, client):
        user = UserFactory()
        client.force_login(user)
        response = client.get(reverse("home"))
        assert response.status_code == 200
        assert b'id="app"' in response.content
        assert b"data-project-name=" in response.content


@pytest.mark.django_db
class TestAuthRoutes:
    """An unmounted auth URL must 404, not 500 on a missing template."""

    def test_login_is_mounted(self, client):
        response = client.get(reverse("login"))
        assert response.status_code == 200

    def test_logout_is_mounted(self, client):
        user = UserFactory()
        client.force_login(user)
        response = client.post(reverse("logout"))
        assert response.status_code == 302

    def test_password_reset_is_not_mounted(self, client):
        response = client.get("/accounts/password_reset/")
        assert response.status_code == 404

    def test_allauth_signup_is_not_mounted(self, client):
        response = client.get("/accounts/signup/")
        assert response.status_code == 404

    def test_password_login_works_for_an_admin_created_user(self, client):
        UserFactory(username="alice")

        response = client.post(
            reverse("login"), {"username": "alice", "password": "pw-12345!"}
        )

        assert response.status_code == 302
        assert response["Location"] == reverse("home")


@pytest.mark.django_db
class TestLoginPage:
    def test_shows_google_button_when_a_client_id_is_set(self, client):
        response = client.get(reverse("login"), {"next": "/api-access/"})

        content = response.content.decode()
        assert "Sign in with Google" in content
        assert 'action="/accounts/google/login/?next=%2Fapi-access%2F"' in content

    def test_hides_google_button_without_a_client_id(self, client, settings):
        settings.SOCIALACCOUNT_PROVIDERS = {}

        response = client.get(reverse("login"))

        assert "Sign in with Google" not in response.content.decode()
