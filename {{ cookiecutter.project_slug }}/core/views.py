from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


@login_required
@ensure_csrf_cookie
def app_view(request: HttpRequest, **kwargs) -> HttpResponse:
    """Render the SPA mount template for every SPA route.

    `@ensure_csrf_cookie` sets the `csrftoken` cookie on first paint so SPA
    writes can echo it via `X-CSRFToken`. Boot data is split by nature; see
    ADR-0006.
    """
    return render(request, "core/app.html")
