from django.http import HttpRequest
from ninja import NinjaAPI
from ninja.security import django_auth

# Optional: the api_keys app provides bearer-token auth for headless callers.
# If you delete the api_keys app, change `auth=[...]` below to `auth=django_auth`
# and remove the api_keys router mount. See docs/adr/0002-api-keys-session-only.md.
from api_keys.api import router as api_keys_router
from api_keys.auth import ApiKeyBearer
from core.schemas import MeOut

# Both auth methods accepted on every endpoint. ninja tries each in order;
# the first that returns a truthy value wins. Bearer is tried before
# django_auth because ninja's session auth runs a CSRF check *before* it
# even reads the session cookie — so on a bearer-authed write request it
# would 403 before ApiKeyBearer ever ran. With bearer first, token-bound
# requests never invoke the CSRF check. Both paths resolve to the same
# `request.user`.
#
# Exception: the `/api/api-keys/*` router overrides this default to
# `django_auth` only — see ADR-0002.
api = NinjaAPI(auth=[ApiKeyBearer(), django_auth])
api.add_router("/api-keys/", api_keys_router)


@api.get("/me", response=MeOut)
def me(request: HttpRequest) -> MeOut:
    """The authenticated user. Inherits the global dual auth, so it serves
    both the SPA boot payload (session) and a headless ``whoami`` (bearer).
    Read-only — no escalation risk on the bearer path."""
    return request.user
