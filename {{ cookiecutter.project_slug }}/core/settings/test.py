import os

from .base import *  # noqa: F403

# Playwright's sync API runs in an event loop, where Django's async-safety guard
# rejects the live_server fixture's DB calls with SynchronousOnlyOperation.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

SECRET_KEY = "test-secret-key-for-testing-only"  # noqa: S105 not a real secret
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

# Not STATIC_ROOT, so `make test` needs `make frontend.build` and no `collectstatic`.
DJANGO_VITE["default"]["manifest_path"] = (  # noqa: F405
    BASE_DIR / "core" / "static" / "dist" / "js" / "manifest.json"  # noqa: F405
)

# Throttle counters must not leak between tests.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
}

RQ_QUEUES["default"]["ASYNC"] = False  # noqa: F405

STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

# Skips whitenoise's STATIC_ROOT scan, which warns "No directory at: staticfiles"
# because the test run never runs collectstatic.
WHITENOISE_AUTOREFRESH = True

SENTRY_DSN = ""

SOCIALACCOUNT_PROVIDERS = google_providers("test-client-id", "test-client-secret")  # noqa: F405
SSO_ALLOWED_DOMAINS = []
SSO_ALLOWED_EMAILS = []
SSO_SUPERUSER_EMAILS = []

# PBKDF2 costs ~0.13s per UserFactory-built test against ~0.005s of actual work.
# Re-profile before removing this.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
