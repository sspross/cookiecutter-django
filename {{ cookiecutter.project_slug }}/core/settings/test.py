from .base import *  # noqa: F403

# Override env with test defaults
SECRET_KEY = "test-secret-key-for-testing-only"
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]

# Use standard static files storage for tests to avoid manifest requirements.
# Tests rely on `make frontend.build && uv run python manage.py collectstatic`
# having been run beforehand so the SPA bundle is on disk.
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
