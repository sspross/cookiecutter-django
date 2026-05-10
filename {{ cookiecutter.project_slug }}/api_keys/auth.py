"""ninja auth class for `Authorization: Bearer <prefix>…` tokens.

Thin adapter: the policy lives in ``api_keys.services``. This module
only adapts the bearer-token protocol to the request/response shape
ninja expects.
"""

from __future__ import annotations

from ninja.security import HttpBearer

from api_keys import services


class ApiKeyBearer(HttpBearer):
    """Resolve a bearer token to ``request.user`` via :func:`services.verify`.

    Returning truthy from ``authenticate`` makes ninja set
    ``request.auth``; we additionally assign ``request.user`` so the rest
    of the API code does not have to know which auth method ran.
    """

    def authenticate(self, request, token: str):
        user = services.verify(token)
        if user is None:
            return None
        # Make request.user mirror django_auth's behaviour. Endpoints rely
        # on this for attribution.
        request.user = user
        return user
