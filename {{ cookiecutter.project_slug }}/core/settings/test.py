from .base import *  # noqa: F403

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

# Plain (non-manifest) staticfiles storage so `{% static %}` lookups in tests
# don't require a collected staticfiles tree.
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
