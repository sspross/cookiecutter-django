"""Token engine for `UserApiKey`.

The public surface is ``mint``, ``verify`` and ``revoke``; the prefix, hashing
and revocation policy stays inside. Callers import neither ``hashlib`` nor
``secrets``, so a policy change touches only this module.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

from django.utils import timezone

from api_keys.models import UserApiKey

TOKEN_PREFIX = "{{ cookiecutter.project_slug }}_live_"
TOKEN_RANDOM_BYTES = 32
DISPLAY_PREFIX_LENGTH = 12


@dataclass(frozen=True)
class MintResult:
    api_key: UserApiKey
    raw_token: str


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def mint(user, name: str) -> MintResult:
    """Generate a new API key for ``user`` and persist only its hash.

    The returned raw token is the sole opportunity any caller has to observe
    the live credential; it is never written back to the database.
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

    Rejects unknown hashes, revoked keys, keys of deactivated users and
    malformed tokens. On success, bumps ``last_used_at``.
    """

    if not raw_token or not raw_token.startswith(TOKEN_PREFIX):
        return None

    try:
        api_key = UserApiKey.objects.select_related("user").get(hash=_hash(raw_token))
    except UserApiKey.DoesNotExist:
        return None

    if api_key.is_revoked or not api_key.user.is_active:
        return None

    UserApiKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
    return api_key.user


def revoke(api_key: UserApiKey) -> None:
    """Mark ``api_key`` revoked. Idempotent — re-revocation is a no-op."""

    if api_key.revoked_at is None:
        api_key.revoked_at = timezone.now()
        api_key.save(update_fields=["revoked_at"])
