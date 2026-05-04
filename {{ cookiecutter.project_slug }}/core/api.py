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

Validation: services raise Django's `ValidationError` from `full_clean`.
A project-wide handler maps that to a 422 response shaped like a Pydantic
422 (`{"detail": [{"loc": [...], "msg": "..."}]}`) so the SPA's RHF helper
consumes both kinds of validation errors uniformly.
"""

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpRequest
from django.middleware.csrf import get_token
from ninja import NinjaAPI, Schema

api = NinjaAPI(title="{{ cookiecutter.project_name }} API")


@api.exception_handler(DjangoValidationError)
def handle_django_validation_error(request: HttpRequest, exc: DjangoValidationError):
    """Map Django's `ValidationError` to a Pydantic-shaped 422 response."""
    detail: list[dict] = []
    if hasattr(exc, "error_dict"):
        for field, errors in exc.message_dict.items():
            for msg in errors:
                detail.append(
                    {
                        "loc": ["body", field],
                        "msg": msg,
                        "type": "validation_error",
                    }
                )
    elif hasattr(exc, "error_list"):
        for err in exc.error_list:
            detail.append(
                {
                    "loc": ["body"],
                    "msg": str(err.message if hasattr(err, "message") else err),
                    "type": "validation_error",
                }
            )
    else:
        detail.append(
            {"loc": ["body"], "msg": str(exc), "type": "validation_error"}
        )
    return api.create_response(request, {"detail": detail}, status=422)


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


# --- App routers -----------------------------------------------------------
# Every Django app contributes endpoints by exporting a `Router`. Mounting
# happens here so the whole project produces a single OpenAPI document.
# Routers are added by Python-path string so this module does not need to
# statically import app code — that keeps `core` free of dependencies on
# the apps that depend on it. Removing an app from the project is two
# edits: drop it from `INSTALLED_APPS` and remove its router mount below.
api.add_router("/example", "example.api.router")
