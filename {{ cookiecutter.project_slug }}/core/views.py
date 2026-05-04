"""Project-wide views.

Currently the only view here is the SPA shell: a catch-all that returns the
Vite-built `index.html` for any non-API, non-admin, non-static, non-media
path. This is what serves the SPA in the WhiteNoise/Appliku deploy path.
The Caddy/compose deploy serves `index.html` directly from disk and never
hits Django for these paths.
"""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.views.decorators.cache import never_cache


@never_cache
def spa_shell(request: HttpRequest) -> HttpResponse:
    """Return the Vite-built index.html as the SPA entry point."""
    index_path = Path(settings.STATIC_ROOT) / "index.html"
    if not index_path.exists():
        # Dev fallback: collectstatic has not run, but the Vite build may
        # still have produced index.html in STATICFILES_DIRS.
        for static_dir in settings.STATICFILES_DIRS:
            candidate = Path(static_dir) / "index.html"
            if candidate.exists():
                index_path = candidate
                break
        else:
            raise Http404(
                "SPA index.html not found. Run `make frontend.build` and "
                "`uv run python manage.py collectstatic --noinput`."
            )
    return FileResponse(index_path.open("rb"), content_type="text/html")
