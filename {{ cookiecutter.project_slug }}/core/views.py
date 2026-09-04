import django_rq
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_safe


def _database_status() -> str:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return "error"
    return "ok"


def _redis_status() -> str:
    try:
        django_rq.get_connection("default").ping()
    except Exception:
        return "error"
    return "ok"


@require_safe
def healthz(request: HttpRequest) -> JsonResponse:
    checks = {"database": _database_status(), "redis": _redis_status()}
    all_ok = all(status == "ok" for status in checks.values())
    return JsonResponse(checks, status=200 if all_ok else 503)


@login_required
@ensure_csrf_cookie
def app_view(request: HttpRequest, **kwargs) -> HttpResponse:
    """Render the SPA mount template for every SPA route.

    `@ensure_csrf_cookie` sets the `csrftoken` cookie on first paint so SPA
    writes can echo it via `X-CSRFToken`. Boot data is split by nature; see
    ADR-0006.
    """
    return render(request, "core/app.html")
