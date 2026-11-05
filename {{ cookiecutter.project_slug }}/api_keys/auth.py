from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import HttpRequest
from ninja.security import HttpBearer

from api_keys import services

if TYPE_CHECKING:
    from users.models import User


class ApiKeyBearer(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> User | None:
        user = services.verify(token)
        if user is None:
            return None
        request.user = user
        return user
