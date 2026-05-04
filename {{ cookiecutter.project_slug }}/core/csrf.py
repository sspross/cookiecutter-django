"""CSRF protection for Ninja mutation endpoints.

Django Ninja decorates its dispatch with `csrf_exempt`, so Django's
`CsrfViewMiddleware` never runs on Ninja routes by default. To enforce CSRF
on mutations (POST/PATCH/PUT/DELETE) attach `@csrf_protect_route` to the
endpoint. The decorator runs Django's standard CSRF check and lets the
request through if the `X-CSRFToken` header (or `csrfmiddlewaretoken` form
field) matches the `csrftoken` cookie minted by `/api/config`.

GETs and other safe methods don't need the decorator — they're CSRF-exempt
by definition.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.middleware.csrf import CsrfViewMiddleware


def _accept(request, response):
    return None


_csrf_middleware = CsrfViewMiddleware(_accept)


def csrf_protect_route(view_func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that runs Django's CSRF check before the wrapped view."""

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        rejection = _csrf_middleware.process_view(request, view_func, args, kwargs)
        if rejection is not None:
            return rejection
        return view_func(request, *args, **kwargs)

    return wrapped
