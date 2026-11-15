import re

import pytest
from django.test import Client

from api_keys import services as api_keys
from api_keys.tests.factories import UserFactory

CHANGELIST_URL = "/admin/api_keys/userapikey/"


@pytest.fixture
def superuser_client(client: Client, db: None) -> Client:
    client.force_login(UserFactory.create(is_superuser=True, is_staff=True))
    return client


class TestUserApiKeyAdmin:
    def test_add_form_mints_a_working_key_for_another_user(
        self, superuser_client: Client
    ) -> None:
        owner = UserFactory.create()

        response = superuser_client.post(
            f"{CHANGELIST_URL}add/", {"user": owner.pk, "name": "ci"}, follow=True
        )

        shown_token = re.search(
            re.escape(api_keys.TOKEN_PREFIX) + r"[\w-]+", response.content.decode()
        )
        assert shown_token is not None
        assert api_keys.verify(shown_token.group()) == owner

    def test_revoke_action_revokes_another_users_key(
        self, superuser_client: Client
    ) -> None:
        result = api_keys.mint(UserFactory.create(), name="ci")

        superuser_client.post(
            CHANGELIST_URL,
            {"action": "revoke_keys", "_selected_action": [result.api_key.pk]},
        )

        assert api_keys.verify(result.raw_token) is None
