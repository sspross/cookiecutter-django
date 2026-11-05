from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.utils import timezone

from api_keys.models import UserApiKey

if TYPE_CHECKING:
    from users.models import User

TOKEN_PREFIX = "{{ cookiecutter.project_slug }}_live_"
TOKEN_RANDOM_BYTES = 32
DISPLAY_PREFIX_LENGTH = 12


@dataclass(frozen=True)
class MintResult:
    api_key: UserApiKey
    raw_token: str


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def mint(user: User, name: str) -> MintResult:
    raw_token = TOKEN_PREFIX + secrets.token_urlsafe(TOKEN_RANDOM_BYTES)
    api_key = UserApiKey.objects.create(
        user=user,
        name=name,
        prefix=raw_token[:DISPLAY_PREFIX_LENGTH],
        hash=_hash(raw_token),
    )
    return MintResult(api_key=api_key, raw_token=raw_token)


def verify(raw_token: str) -> User | None:
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
    if api_key.revoked_at is None:
        api_key.revoked_at = timezone.now()
        api_key.save(update_fields=["revoked_at"])
