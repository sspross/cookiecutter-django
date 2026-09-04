"""ninja router for `/api/api-keys/*` — self-service API key management.

Overrides the global ``[ApiKeyBearer(), django_auth]`` default with
``django_auth`` only, so a leaked bearer token cannot mint a sibling.
See ADR-0002. A thin adapter over :mod:`api_keys.services`.
"""

from __future__ import annotations

from django.http import Http404, HttpRequest
from ninja import Router
from ninja.responses import Status
from ninja.security import django_auth
from ninja.throttling import AuthRateThrottle

from api_keys import services as api_keys_services
from api_keys.models import UserApiKey
from api_keys.schemas import ApiKeyCreateIn, ApiKeyMintOut, ApiKeyOut

router = Router(tags=["api-keys"], auth=django_auth)

MINT_RATE = "10/h"


@router.get("/", response=list[ApiKeyOut])
def list_api_keys(request: HttpRequest):
    """List the requesting user's keys, including revoked, newest-first."""
    return UserApiKey.objects.filter(user=request.user)


@router.post(
    "/",
    response={201: ApiKeyMintOut},
    throttle=[AuthRateThrottle(MINT_RATE)],
)
def create_api_key(request: HttpRequest, payload: ApiKeyCreateIn):
    """Mint a new key and return the raw token exactly once."""
    result = api_keys_services.mint(request.user, payload.name)
    return Status(
        201,
        {
            "api_key": result.api_key,
            "raw_token": result.raw_token,
        },
    )


@router.post("/{api_key_id}/revoke/", response=ApiKeyOut)
def revoke_api_key(request: HttpRequest, api_key_id: int):
    """Revoke a key. Idempotent. Returns 404 for keys not owned by the
    requesting user (existence is not disclosed)."""
    try:
        api_key = UserApiKey.objects.get(pk=api_key_id, user=request.user)
    except UserApiKey.DoesNotExist as exc:
        raise Http404 from exc
    api_keys_services.revoke(api_key)
    return api_key
