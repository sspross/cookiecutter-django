from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from ninja import NinjaAPI
from ninja.security import django_auth

from api_keys.api import router as api_keys_router
from api_keys.auth import ApiKeyBearer
from core.schemas import MeOut
from users.models import User

# Bearer first: django_auth's CSRF check runs before it reads the session cookie,
# so it would 403 a bearer-authed write before ApiKeyBearer ran.
api = NinjaAPI(auth=[ApiKeyBearer(), django_auth])
api.add_router("/api-keys/", api_keys_router)


@api.get("/me", response=MeOut)
def me(request: HttpRequest) -> User | AnonymousUser:
    return request.user
