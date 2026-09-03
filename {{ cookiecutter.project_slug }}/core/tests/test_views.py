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
