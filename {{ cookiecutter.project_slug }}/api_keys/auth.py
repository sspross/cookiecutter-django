"""ninja auth class for `Authorization: Bearer <prefix>…` tokens.

A thin adapter over ``api_keys.services``, which owns the policy.
"""

from __future__ import annotations

from ninja.security import HttpBearer

from api_keys import services


class ApiKeyBearer(HttpBearer):
    """Resolve a bearer token to ``request.user`` via :func:`services.verify`."""

    def authenticate(self, request, token: str):
        user = services.verify(token)
        if user is None:
            return None
        # Make request.user mirror django_auth's behaviour. Endpoints rely
        # on this for attribution.
        request.user = user
        return user
