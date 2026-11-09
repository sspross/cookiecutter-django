import json
import os
import subprocess
import sys

import pytest
from django.conf import settings

PRINT_HTTPS_SETTINGS = """
import json
import django
django.setup()
from django.conf import settings
print(json.dumps({
    "redirect": getattr(settings, "SECURE_SSL_REDIRECT", False),
    "secure_session_cookie": getattr(settings, "SESSION_COOKIE_SECURE", False),
    "secure_csrf_cookie": getattr(settings, "CSRF_COOKIE_SECURE", False),
    "hsts_seconds": getattr(settings, "SECURE_HSTS_SECONDS", 0),
}))
"""

ENFORCED = {
    "redirect": True,
    "secure_session_cookie": True,
    "secure_csrf_cookie": True,
    "hsts_seconds": 60 * 60 * 24 * 365,
}
NOT_ENFORCED = {
    "redirect": False,
    "secure_session_cookie": False,
    "secure_csrf_cookie": False,
    "hsts_seconds": 0,
}


def production_settings(**overrides: str) -> dict[str, object]:
    """Imports the real settings in a fresh interpreter, because they are read from
    the environment once, at import time."""
    environment = {
        key: value for key, value in os.environ.items() if key != "HTTPS_ENFORCED"
    }
    environment |= {
        "DJANGO_SETTINGS_MODULE": "core.settings",
        "DEBUG": "false",
        "SECRET_KEY": "https-enforcement-test-secret-key",
        "DATABASE_URL": "sqlite://:memory:",
    }
    environment |= overrides
    result = subprocess.run(
        [sys.executable, "-c", PRINT_HTTPS_SETTINGS],
        cwd=settings.BASE_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    https_settings: dict[str, object] = json.loads(result.stdout)
    return https_settings


def test_https_is_enforced_by_default() -> None:
    assert production_settings() == ENFORCED


@pytest.mark.parametrize("value", ["", "0", "no", "off", "False "])
def test_https_stays_enforced_unless_the_value_is_exactly_false(value: str) -> None:
    assert production_settings(HTTPS_ENFORCED=value) == ENFORCED


@pytest.mark.parametrize("value", ["false", "FALSE"])
def test_https_enforcement_is_off_only_with_an_explicit_false(value: str) -> None:
    assert production_settings(HTTPS_ENFORCED=value) == NOT_ENFORCED
