"""Model-level tests for ``UserApiKey``.

Only ``__str__`` lives here; no other test reaches it. Ordering, ``is_revoked``
and the revocation transition are asserted where they are observable, through
the API and through ``services.verify``.
"""

import pytest

from api_keys import services as api_keys
from api_keys.tests.factories import UserFactory


@pytest.mark.django_db
class TestUserApiKeyStr:
    def test_str_includes_owner_name_and_prefix(self):
        user = UserFactory(username="alice")
        result = api_keys.mint(user, name="laptop")

        rendered = str(result.api_key)

        assert "alice" in rendered
        assert "laptop" in rendered
        assert result.api_key.prefix in rendered

    def test_str_marks_revoked(self):
        user = UserFactory()
        result = api_keys.mint(user, name="rotated")
        api_keys.revoke(result.api_key)
        result.api_key.refresh_from_db()

        assert "(revoked)" in str(result.api_key)
