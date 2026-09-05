"""Sentry wiring: error events and application logs, no tracing (ADR-0007).

Initialized from ``core.apps.CoreConfig.ready`` rather than from a settings
module, because ``core/settings/test.py`` blanks the DSN only after
``base.py`` has already run.
"""

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

__all__ = ["DEFAULT_ENVIRONMENT", "init_sentry", "sentry_options"]

DEFAULT_ENVIRONMENT = "production"


def sentry_options(dsn: str, environment: str = DEFAULT_ENVIRONMENT) -> dict[str, Any]:
    """Split out of :func:`init_sentry` so tests can build a client on the real
    options with a capturing transport."""

    return {
        "dsn": dsn,
        "environment": environment,
        "integrations": [
            DjangoIntegration(),
            # Listed explicitly because `capture_sentry_logs` defaults to off;
            # `enable_logs`, its old switch, became a no-op in sentry-sdk 2.68.
            # Both levels override SDK defaults that would otherwise be a second
            # event and log policy (ADR-0007).
            LoggingIntegration(
                capture_sentry_logs=True,
                event_level=None,
                sentry_logs_level=logging.NOTSET,
            ),
        ],
        "auto_session_tracking": False,
    }


def init_sentry(dsn: str, environment: str = DEFAULT_ENVIRONMENT) -> bool:
    if not dsn:
        return False
    sentry_sdk.init(**sentry_options(dsn, environment))
    return True
