import pytest

from api_keys import services as api_keys
from api_keys.models import UserApiKey
from api_keys.tests.factories import UserFactory


@pytest.mark.django_db
class TestUserApiKeyModel:
    def test_str_includes_prefix(self):
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

    def test_is_revoked_property(self):
        user = UserFactory()
        result = api_keys.mint(user, name="ci")

        assert result.api_key.is_revoked is False

        api_keys.revoke(result.api_key)
        result.api_key.refresh_from_db()
        assert result.api_key.is_revoked is True

    def test_default_ordering_is_newest_first(self):
        user = UserFactory()
        first = api_keys.mint(user, name="first").api_key
        second = api_keys.mint(user, name="second").api_key

        rows = list(UserApiKey.objects.all())

        assert rows == [second, first]
