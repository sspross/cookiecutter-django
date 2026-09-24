import pytest
from django.test import Client

from api_keys.tests.factories import UserFactory
from users.models import User


@pytest.fixture
def superuser(db: None) -> User:
    return UserFactory(username="root", is_superuser=True, is_staff=True)


@pytest.fixture
def superuser_client(client: Client, superuser: User) -> Client:
    client.force_login(superuser)
    return client


@pytest.mark.django_db
class TestUserAdmin:
    def test_changelist_links_to_the_user(
        self, superuser_client: Client, superuser: User
    ) -> None:
        response = superuser_client.get("/admin/users/user/")

        assert response.status_code == 200
        assert f"/admin/users/user/{superuser.pk}/change/".encode() in response.content

    def test_add_form_renders(self, superuser_client: Client) -> None:
        response = superuser_client.get("/admin/users/user/add/")

        assert response.status_code == 200
