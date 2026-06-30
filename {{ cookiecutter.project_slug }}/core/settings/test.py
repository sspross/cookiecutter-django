import os

from .base import *  # noqa: F403

# Live tests drive a browser through Playwright's sync API, which runs in an
# event loop. Django's async-safety guard would reject the live_server
# fixture's DB calls from that loop with SynchronousOnlyOperation; relax the
# guard for the whole test run. It's a no-op for non-live tests (they never
# enter an async context). Replaces the env-var the old base class set.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

# Override env with test defaults before importing base
SECRET_KEY = "test-secret-key-for-testing-only"
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]

# Read the Vite manifest from the per-app build output rather than STATIC_ROOT,
# so `make test` only needs `make frontend.build` (no `collectstatic` step).
DJANGO_VITE["default"]["dev_mode"] = False  # noqa: F405
DJANGO_VITE["default"]["manifest_path"] = (  # noqa: F405
    BASE_DIR / "core" / "static" / "dist" / "js" / "manifest.json"  # noqa: F405
)

# Run enqueued jobs inline on the calling thread instead of handing them to a
# worker, so `.delay()` resolves synchronously in tests (no Redis round-trip,
# no separate process). Matches the claim in core/settings/base.py. See ADR-0003.
RQ_QUEUES["default"]["ASYNC"] = False  # noqa: F405

# Plain (non-manifest) staticfiles storage so `{% raw %}{% static %}{% endraw %}` lookups in tests
# don't require a collected staticfiles tree.
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
