import json
import logging
import os
import subprocess
import sys
from typing import Any

import pytest
import sentry_sdk
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.http import HttpRequest, HttpResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import path
from ninja import NinjaAPI

from core.observability import DEFAULT_ENVIRONMENT, init_sentry, sentry_options
from core.tests.sentry_capture import TEST_DSN, CapturingTransport, flush_sentry

BOOT_PROBE = """
import json

import django

django.setup()

import sentry_sdk

client = sentry_sdk.get_client()
print(json.dumps({"active": client.is_active(), "dsn": getattr(client, "dsn", None)}))
"""


def boom(request: HttpRequest) -> HttpResponse:
    raise RuntimeError("web boom")


test_api = NinjaAPI(urls_namespace="observability-test", auth=None)


@test_api.get("/boom")
def api_boom(request: HttpRequest) -> None:
    raise RuntimeError("api boom")


urlpatterns = [path("boom", boom), path("test-api/", test_api.urls)]


def boot(settings_module: str, **environment: str) -> dict[str, Any]:
    # A child process because SDK initialization happens once per process during
    # ``django.setup()``, which the suite has already passed.
    result = subprocess.run(
        [sys.executable, "-c", BOOT_PROBE],
        cwd=settings.BASE_DIR,
        env={**os.environ, "DJANGO_SETTINGS_MODULE": settings_module, **environment},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


class TestInitialization:
    def test_a_blank_dsn_initializes_nothing(self) -> None:
        assert init_sentry("", DEFAULT_ENVIRONMENT) is False
        assert sentry_sdk.get_client().is_active() is False

    def test_the_suite_runs_with_no_client(self) -> None:
        assert settings.SENTRY_DSN == ""
        assert sentry_sdk.get_client().is_active() is False

    def test_the_test_settings_win_over_a_dsn_in_the_environment(self) -> None:
        assert boot("core.settings.test", SENTRY_DSN=TEST_DSN)["active"] is False

    def test_the_deployed_settings_initialize_from_the_environment(self) -> None:
        client = boot("core.settings.base", SENTRY_DSN=TEST_DSN)
        assert client["active"] is True
        assert client["dsn"] == TEST_DSN

    def test_the_environment_defaults_to_production(self) -> None:
        assert DEFAULT_ENVIRONMENT == "production"
        assert settings.SENTRY_ENVIRONMENT == "production"
        assert sentry_options(TEST_DSN)["environment"] == "production"

    def test_the_options_carry_the_django_and_logging_integrations(self) -> None:
        integrations = {
            type(integration).__name__
            for integration in sentry_options(TEST_DSN, "test")["integrations"]
        }
        assert {"DjangoIntegration", "LoggingIntegration"} <= integrations

    def test_nothing_is_traced(self) -> None:
        options = sentry_options(TEST_DSN, "test")
        assert "traces_sample_rate" not in options
        assert options["auto_session_tracking"] is False


@pytest.mark.django_db
class TestErrorEvents:
    def test_an_unhandled_web_exception_becomes_an_event(
        self, client: Client, sentry: CapturingTransport
    ) -> None:
        client.raise_request_exception = False
        with override_settings(ROOT_URLCONF=__name__):
            response = client.get("/boom")
        assert response.status_code == 500
        flush_sentry()
        assert len(sentry.events()) == 1
        event = sentry.event_with("web boom")
        assert event["transaction"] == "/boom"

    def test_an_unhandled_ninja_exception_becomes_an_event(
        self, client: Client, sentry: CapturingTransport
    ) -> None:
        # ninja re-raises an unhandled exception only when DEBUG is off; with
        # DEBUG on it renders the traceback itself and Django never sees it.
        assert settings.DEBUG is False
        client.raise_request_exception = False
        with override_settings(ROOT_URLCONF=__name__):
            response = client.get("/test-api/boom")
        assert response.status_code == 500
        flush_sentry()
        assert len(sentry.events()) == 1
        event = sentry.event_with("api boom")
        assert event["transaction"] == "/test-api/boom"

    def test_an_application_error_log_is_a_log_and_not_an_event(
        self, sentry: CapturingTransport
    ) -> None:
        # The policy under test is ADR-0007.
        logger = logging.getLogger("core.services")
        logger.error("attempt 1/3 failed (transport), retrying in 60 s")
        try:
            raise RuntimeError("swallowed boom")
        except RuntimeError:
            logger.exception("attempt 3/3 failed, needs attention")
        flush_sentry()
        assert sentry.event_messages() == []
        assert "attempt 1/3 failed (transport), retrying in 60 s" in (
            sentry.log_bodies()
        )
        assert "attempt 3/3 failed, needs attention" in sentry.log_bodies()

    def test_an_explicit_capture_is_an_event(self, sentry: CapturingTransport) -> None:
        sentry_sdk.capture_exception(RuntimeError("terminal boom"))
        flush_sentry()
        assert "terminal boom" in sentry.event_messages()


@pytest.mark.django_db
class TestHealthzIsSilent:
    def test_the_probe_generates_no_sentry_traffic(
        self, sentry: CapturingTransport
    ) -> None:
        # Driven through the WSGI application rather than the test client: the
        # SDK's request handling lives in ``WSGIHandler.__call__``, which the
        # test client bypasses.
        application = get_wsgi_application()
        environ = RequestFactory(headers={"host": "localhost"}).get("/healthz").environ
        statuses: list[str] = []
        body = b"".join(
            application(environ, lambda status, headers: statuses.append(status))
        )
        assert statuses == ["200 OK"]
        assert json.loads(body) == {"database": "ok", "redis": "ok"}

        flush_sentry()
        assert sentry.item_types() == []
