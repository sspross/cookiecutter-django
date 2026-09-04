import os

from .base import *  # noqa: F403

# Playwright's sync API runs in an event loop, where Django's async-safety
# guard rejects the live_server fixture's DB calls with SynchronousOnlyOperation.
# A no-op for non-live tests, which never enter an async context.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

SECRET_KEY = "test-secret-key-for-testing-only"
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["http://localhost", "http://127.0.0.1"]

# The test client and live_server speak plain HTTP.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

# Read the Vite manifest from the per-app build output rather than STATIC_ROOT,
# so `make test` only needs `make frontend.build` (no `collectstatic` step).
DJANGO_VITE["default"]["dev_mode"] = False  # noqa: F405
DJANGO_VITE["default"]["manifest_path"] = (  # noqa: F405
    BASE_DIR / "core" / "static" / "dist" / "js" / "manifest.json"  # noqa: F405
)

# Run enqueued jobs inline on the calling thread, so `.delay()` resolves
# synchronously with no Redis round-trip and no worker process. See ADR-0003.
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

# The default PBKDF2 hasher is deliberately slow and dominated the suite:
# ~0.13s per UserFactory-built test against ~0.005s of actual work. MD5 keeps
# set_password/check_password honest. Re-profile before removing this.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
