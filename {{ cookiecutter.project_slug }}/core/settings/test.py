import environ

from .base import *  # noqa: F403

# Override env with test defaults before importing base
env = environ.Env(
    SECRET_KEY=(str, "test-secret-key-for-testing-only"),
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSRF_TRUSTED_ORIGINS=(list, ["http://localhost", "http://127.0.0.1"]),
)

# Use standard static files storage for tests to avoid manifest requirements
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
