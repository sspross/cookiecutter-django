import json
import os
import subprocess
import sys
from collections.abc import Iterable

from django.conf import settings

PRINT_SETTINGS = """
import json
import sys
import django
django.setup()
from django.conf import settings
print(json.dumps({name: getattr(settings, name) for name in sys.argv[1:]}))
"""


def production_settings(
    names: Iterable[str], unset: Iterable[str] = (), **overrides: str
) -> dict[str, object]:
    """Imports the real settings in a fresh interpreter, because they are read from
    the environment once, at import time."""
    cleared = set(unset)
    environment = {
        key: value for key, value in os.environ.items() if key not in cleared
    }
    environment |= {
        "DJANGO_SETTINGS_MODULE": "core.settings",
        "DEBUG": "false",
        "SECRET_KEY": "fresh-settings-test-secret-key",
        "DATABASE_URL": "sqlite://:memory:",
    }
    environment |= overrides
    result = subprocess.run(
        [sys.executable, "-c", PRINT_SETTINGS, *names],
        cwd=settings.BASE_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    values: dict[str, object] = json.loads(result.stdout)
    return values
