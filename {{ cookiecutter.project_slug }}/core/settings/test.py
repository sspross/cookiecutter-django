from .base import *  # noqa: F403

# Override env with test defaults before importing base
SECRET_KEY = "test-secret-key-for-testing-only"
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]

# We want to use builded and collected static files instead of a live server.
# `make frontend.build && uv run python manage.py collectstatic --noinput`
DJANGO_VITE["default"]["dev_mode"] = False  # noqa: F405

# Use standard static files storage for tests to avoid manifest requirements
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
