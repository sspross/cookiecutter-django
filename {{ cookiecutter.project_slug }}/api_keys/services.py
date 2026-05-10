"""Token engine for `UserApiKey`.

A deep module: the public surface is two functions — ``mint`` and
``verify`` — and the prefix/hashing/revocation policy stays inside.
Callers (admin actions, ninja auth class) do not import ``hashlib`` or
``secrets``; if the policy ever changes, only this module updates.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.utils import timezone

from api_keys.models import UserApiKey

TOKEN_PREFIX = "{{ cookiecutter.project_slug }}_live_"
TOKEN_RANDOM_BYTES = 32
DISPLAY_PREFIX_LENGTH = 12


@dataclass(frozen=True)
class MintResult:
    """Return value of ``mint``: the persisted row + the one-shot raw token."""

    api_key: UserApiKey
    raw_token: str


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def mint(user, name: str) -> MintResult:
    """Generate a new API key for ``user`` and persist its hash.

    Returns the freshly-created ``UserApiKey`` row alongside the raw token,
    which is the only opportunity any caller has to observe the live
    credential. The raw token is never written back to the database.
    """

    raw_token = TOKEN_PREFIX + secrets.token_urlsafe(TOKEN_RANDOM_BYTES)
    api_key = UserApiKey.objects.create(
        user=user,
        name=name,
        prefix=raw_token[:DISPLAY_PREFIX_LENGTH],
        hash=_hash(raw_token),
    )
    return MintResult(api_key=api_key, raw_token=raw_token)


def verify(raw_token: str):
    """Resolve a raw bearer token to its owning user, or ``None``.

    Rejects: unknown hashes, revoked keys, malformed/tampered tokens.
    On success, bumps ``last_used_at`` so the admin can identify dormant
    keys.
    """

    if not raw_token or not raw_token.startswith(TOKEN_PREFIX):
        return None

    try:
        api_key = UserApiKey.objects.select_related("user").get(hash=_hash(raw_token))
    except UserApiKey.DoesNotExist:
        return None

    if api_key.is_revoked:
        return None

    UserApiKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
    return api_key.user


def revoke(api_key: UserApiKey) -> None:
    """Mark ``api_key`` revoked. Idempotent — re-revocation is a no-op."""

    if api_key.revoked_at is None:
        api_key.revoked_at = timezone.now()
        api_key.save(update_fields=["revoked_at"])


# Re-export the user model for ergonomic typing without importing all over.
User = get_user_model()
