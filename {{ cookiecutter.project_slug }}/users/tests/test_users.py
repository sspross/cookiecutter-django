import pytest
from django.core.management import call_command
from django.test import Client

from api_keys.tests.factories import UserFactory
from users.models import User


@pytest.mark.django_db
class TestSeedFixture:
    def test_loaddata_seeds_the_default_superuser(self) -> None:
        call_command("loaddata", "dumpdata.json", verbosity=0)

        user = User.objects.get(username="{{ cookiecutter.django_username }}")
        assert user.is_superuser
        assert user.is_staff


@pytest.mark.django_db
class TestUserAdmin:
    def test_changelist_renders_for_superuser(self, client: Client) -> None:
        superuser = UserFactory(username="root", is_superuser=True, is_staff=True)
        client.force_login(superuser)

        response = client.get("/admin/users/user/")

        assert response.status_code == 200
        assert b"root" in response.content

    def test_add_form_renders_for_superuser(self, client: Client) -> None:
        superuser = UserFactory(username="root", is_superuser=True, is_staff=True)
        client.force_login(superuser)

        response = client.get("/admin/users/user/add/")

        assert response.status_code == 200
