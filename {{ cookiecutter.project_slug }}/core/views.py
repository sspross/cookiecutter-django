from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


@login_required
@ensure_csrf_cookie
def app_view(request: HttpRequest, **kwargs) -> HttpResponse:
    """Render the SPA mount template.

    A thin Django shell with `<div id="app">` plus the django-vite asset
    tag for `main.tsx`. `@ensure_csrf_cookie` guarantees the `csrftoken`
    cookie is set on first paint so SPA write requests can echo it via
    `X-CSRFToken`.

    Build-time constants reach the SPA by server-render: `project_name`
    (injected by the `core.context.site` context processor) becomes the
    `data-project-name` attribute on `#app`. Per-user boot data is *not*
    inlined here — the SPA fetches it from the typed `/api/me`. See ADR-0006.

    Same view answers both `/` and `/api-access/` — react-router reads
    the path off `window.location` after mount; server-side routing only
    needs to match these two patterns to support hard reloads.
    """
    return render(request, "core/app.html")
