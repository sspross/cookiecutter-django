"""Tests for the API key token engine.

These assertions cover only the public surface (``mint`` / ``verify`` /
``revoke``) and observable side effects (the persisted ``UserApiKey``
row, ``last_used_at`` updates, the prefix on the raw token). Internal
helpers — the hash function, the random source — are deliberately not
poked, so the tests survive a reorganisation of the engine internals.
"""

import pytest

from api_keys import services as api_keys
from api_keys.models import UserApiKey
from api_keys.tests.factories import UserFactory


@pytest.mark.django_db
class TestMint:
    def test_mint_returns_prefixed_raw_token(self):
        user = UserFactory()

        result = api_keys.mint(user, name="ci")

        assert result.raw_token.startswith(api_keys.TOKEN_PREFIX)
        assert len(result.raw_token) > len(api_keys.TOKEN_PREFIX) + 16

    def test_mint_persists_user_api_key_row(self):
        user = UserFactory()

        result = api_keys.mint(user, name="ci")

        api_key = UserApiKey.objects.get(pk=result.api_key.pk)
        assert api_key.user == user
        assert api_key.name == "ci"
        assert api_key.prefix == result.raw_token[:12]

    def test_mint_does_not_persist_raw_token(self):
        """The raw token must not be reachable from the database."""
        user = UserFactory()

        result = api_keys.mint(user, name="ci")

        api_key = UserApiKey.objects.get(pk=result.api_key.pk)
        assert api_key.hash != result.raw_token


@pytest.mark.django_db
class TestVerify:
    def test_round_trip(self):
        user = UserFactory()
        result = api_keys.mint(user, name="ci")

        verified = api_keys.verify(result.raw_token)

        assert verified == user

    def test_unknown_token_returns_none(self):
        assert api_keys.verify(api_keys.TOKEN_PREFIX + "doesnotexist") is None

    def test_token_without_prefix_returns_none(self):
        assert api_keys.verify("not-prefixed") is None

    def test_empty_token_returns_none(self):
        assert api_keys.verify("") is None

    def test_tampered_token_is_rejected(self):
        user = UserFactory()
        result = api_keys.mint(user, name="ci")
        # Flip a single character in the random portion.
        tampered = result.raw_token[:-1] + (
            "a" if result.raw_token[-1] != "a" else "b"
        )

        assert api_keys.verify(tampered) is None

    def test_revoked_key_is_rejected(self):
        user = UserFactory()
        result = api_keys.mint(user, name="ci")

        api_keys.revoke(result.api_key)

        assert api_keys.verify(result.raw_token) is None

    def test_successful_verify_bumps_last_used_at(self):
        user = UserFactory()
        result = api_keys.mint(user, name="ci")
        assert result.api_key.last_used_at is None

        api_keys.verify(result.raw_token)

        result.api_key.refresh_from_db()
        assert result.api_key.last_used_at is not None
