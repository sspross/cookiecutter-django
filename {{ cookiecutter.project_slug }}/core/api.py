from django.http import HttpRequest
from ninja import NinjaAPI
from ninja.security import django_auth

# The api_keys app is optional: dropping it means `auth=django_auth` below and
# no router mount.
from api_keys.api import router as api_keys_router
from api_keys.auth import ApiKeyBearer
from core.schemas import MeOut

# Order matters: ninja's django_auth runs a CSRF check *before* it reads the
# session cookie, so a bearer-authed write would 403 before ApiKeyBearer ever
# ran. Bearer first keeps token-bound requests out of the CSRF path.
api = NinjaAPI(auth=[ApiKeyBearer(), django_auth])
api.add_router("/api-keys/", api_keys_router)


@api.get("/me", response=MeOut)
def me(request: HttpRequest) -> MeOut:
    """The authenticated user. Inherits the global dual auth, so it serves
    both the SPA boot payload (session) and a headless ``whoami`` (bearer).
    Read-only — no escalation risk on the bearer path."""
    return request.user
