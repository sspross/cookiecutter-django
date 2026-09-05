"""Sentry wiring: error events and application logs, no tracing (ADR-0007).

Initialized from ``core.apps.CoreConfig.ready`` rather than from a settings
module, because ``core/settings/test.py`` blanks the DSN only after
``base.py`` has already run.
"""

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import (
    LoggingIntegration,
    ignore_logger,
    ignore_logger_for_sentry_logs,
)
from sentry_sdk.integrations.rq import RqIntegration

__all__ = [
    "DEFAULT_ENVIRONMENT",
    "IGNORED_LOGGERS",
    "init_sentry",
    "sentry_options",
]

DEFAULT_ENVIRONMENT = "production"

# Muted for Sentry at every level, console handler untouched: rq's worker,
# scheduler and job loggers set their own INFO level at startup and ignore
# settings.LOGGING, and an invalid HTTP_HOST is a bot Django already answers
# with a 400.
IGNORED_LOGGERS = (
    "rq.worker",
    "rq.scheduler",
    "rq.job",
    "django.security.DisallowedHost",
)


def _apply_ignored_loggers() -> None:
    """``ignore_logger`` covers events and breadcrumbs only; Sentry Logs are
    filtered against a second list, so both calls are needed to mute a logger."""

    for name in IGNORED_LOGGERS:
        ignore_logger(name)
        ignore_logger_for_sentry_logs(name)


def sentry_options(dsn: str, environment: str = DEFAULT_ENVIRONMENT) -> dict[str, Any]:
    """Split out of :func:`init_sentry` so tests can build a client on the real
    options with a capturing transport."""

    _apply_ignored_loggers()
    return {
        "dsn": dsn,
        "environment": environment,
        "integrations": [
            DjangoIntegration(),
            RqIntegration(),
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
