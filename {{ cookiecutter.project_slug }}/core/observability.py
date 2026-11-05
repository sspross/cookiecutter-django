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

from core.request_context import tag_event_from_exception

__all__ = [
    "DEFAULT_ENVIRONMENT",
    "IGNORED_LOGGERS",
    "init_sentry",
    "sentry_options",
]

DEFAULT_ENVIRONMENT = "production"

IGNORED_LOGGERS = (
    "rq.worker",
    "rq.scheduler",
    "rq.job",
    "django.security.DisallowedHost",
)


def _apply_ignored_loggers() -> None:
    for name in IGNORED_LOGGERS:
        ignore_logger(name)
        ignore_logger_for_sentry_logs(name)


def sentry_options(dsn: str, environment: str = DEFAULT_ENVIRONMENT) -> dict[str, Any]:
    _apply_ignored_loggers()
    return {
        "dsn": dsn,
        "environment": environment,
        "integrations": [
            DjangoIntegration(),
            RqIntegration(),
            # Listed because `capture_sentry_logs` defaults to off. Levels: ADR-0007.
            LoggingIntegration(
                capture_sentry_logs=True,
                event_level=None,
                sentry_logs_level=logging.NOTSET,
            ),
        ],
        "before_send": tag_event_from_exception,
        "auto_session_tracking": False,
    }


def init_sentry(dsn: str, environment: str = DEFAULT_ENVIRONMENT) -> bool:
    if not dsn:
        return False
    sentry_sdk.init(**sentry_options(dsn, environment))
    return True
