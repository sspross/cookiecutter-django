"""Shared Django Ninja API instance for the project.

Every Django app contributes its endpoints by exporting a `Router` that is
mounted on this single `NinjaAPI`. The result is one OpenAPI document for
the whole project, which is what the SPA's openapi-typescript codegen
consumes.

CSRF model: GETs are unprotected (idempotent reads). Mutations attach the
`csrf_protect` decorator from `core.csrf` so Django's CSRF middleware runs
and rejects requests without a valid `X-CSRFToken` header. The SPA primes
that header by calling `/api/config` once on startup, which mints the
`csrftoken` cookie via `get_token`.
"""

from django.conf import settings
from django.http import HttpRequest
from django.middleware.csrf import get_token
from ninja import NinjaAPI, Schema

api = NinjaAPI(title="{{ cookiecutter.project_name }} API")


class HealthOut(Schema):
    status: str


class ConfigOut(Schema):
    project_name: str
    debug: bool


@api.get("/health", response=HealthOut, tags=["core"])
def health(request: HttpRequest) -> HealthOut:
    """Liveness probe used by container healthchecks and the SPA bootstrap."""
    return HealthOut(status="ok")


@api.get("/config", response=ConfigOut, tags=["core"])
def config(request: HttpRequest) -> ConfigOut:
    """Bootstrap call that returns runtime config and mints the CSRF cookie.

    Calling `get_token` here forces Django to set the `csrftoken` cookie on
    the response. The SPA fires this once on startup so subsequent mutations
    can read the cookie and attach it as the `X-CSRFToken` header.
    """
    get_token(request)
    return ConfigOut(
        project_name="{{ cookiecutter.project_name }}",
        debug=settings.DEBUG,
    )
