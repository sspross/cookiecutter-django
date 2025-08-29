"""
Test-specific settings for {{ cookiecutter.project_name }}.
"""

from .base import *  # noqa: F403, F401

# Override settings for testing
DEBUG = True

# Use a faster password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use in-memory cache for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Disable migrations during tests for speed
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


# Uncomment to disable migrations during tests (speeds up test runs)
# MIGRATION_MODULES = DisableMigrations()

# Allow async database operations in tests
# Required for Playwright tests with async event loops
import os
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"