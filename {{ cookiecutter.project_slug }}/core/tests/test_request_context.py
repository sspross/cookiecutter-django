import logging
import re
from collections.abc import Callable
from unittest import mock

import pytest
import redis
import sentry_sdk
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.test import Client, override_settings
from django.urls import path
from pytest_django.fixtures import Settings

from api_keys.tests.factories import UserFactory
from core.request_context import bound
from core.tests.probes import PROBE_MESSAGE
from core.tests.sentry_capture import CapturingTransport, flush_sentry

REQUEST_ID = re.compile(r"\A[0-9a-f]{32}\Z")

PROBE_LOGGER = "core.tests.probes"

REQUEST_LOGGER = "django.request"
DISALLOWED_HOST_LOGGER = "django.security.DisallowedHost"

# In neither ``ALLOWED_HOSTS`` nor the test runner's own additions to it, so
# reading it raises ``DisallowedHost`` inside the middleware stack.
UNKNOWN_HOST = "not-an-allowed-host.example.com"

SURFACES = ("spa page", "internal api", "healthz", "admin")

type Call = Callable[..., HttpResponse]


def boom(request: HttpRequest) -> HttpResponse:
    raise RuntimeError("request context boom")


urlpatterns = [path("boom", boom)]


def _healthz(client: Client, **extra: str) -> HttpResponse:
    # The root CI job has no Redis, so the probe is mocked at that boundary.
    with mock.patch.object(redis.Redis, "ping", return_value=True):
        return client.get("/healthz", **extra)


@pytest.fixture
def probed(settings: Settings) -> None:
    # Appended last so the probe runs innermost, inside the request-id binding.
    settings.MIDDLEWARE = [
        *settings.MIDDLEWARE,
        "core.tests.probes.LoggingProbeMiddleware",
    ]


@pytest.fixture
def call(db: None, client: Client, probed: None) -> dict[str, Call]:
    client.force_login(UserFactory(username="operator", is_staff=True))
    return {
        "spa page": lambda **extra: client.get("/", **extra),
        "internal api": lambda **extra: client.get("/api/me", **extra),
        "healthz": lambda **extra: _healthz(client, **extra),
        "admin": lambda **extra: client.get("/admin/", **extra),
    }


def _only_record(caplog: pytest.LogCaptureFixture, logger: str) -> logging.LogRecord:
    records = [record for record in caplog.records if record.name == logger]
    assert len(records) == 1, [record.getMessage() for record in records]
    return records[0]


def _probe_record(caplog: pytest.LogCaptureFixture) -> logging.LogRecord:
    record = _only_record(caplog, PROBE_LOGGER)
    assert record.getMessage() == PROBE_MESSAGE
    return record


@pytest.mark.django_db
class TestRequestIdHeader:
    @pytest.mark.parametrize("surface", SURFACES)
    def test_every_surface_answers_with_a_request_id(
        self, call: dict[str, Call], surface: str
    ) -> None:
        response = call[surface]()

        assert REQUEST_ID.match(response["X-Request-ID"])

    def test_each_request_gets_an_id_of_its_own(self, call: dict[str, Call]) -> None:
        first = call["internal api"]()["X-Request-ID"]
        second = call["internal api"]()["X-Request-ID"]

        assert first != second

    @pytest.mark.parametrize("surface", SURFACES)
    def test_an_inbound_request_id_is_ignored(
        self, call: dict[str, Call], surface: str
    ) -> None:
        sent = "f" * 32

        response = call[surface](HTTP_X_REQUEST_ID=sent)

        assert response["X-Request-ID"] != sent
        assert REQUEST_ID.match(response["X-Request-ID"])


@pytest.mark.django_db
class TestLogRecordAttributes:
    @pytest.mark.parametrize("surface", SURFACES)
    def test_records_carry_the_id_the_caller_was_given(
        self, call: dict[str, Call], surface: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger=PROBE_LOGGER):
            response = call[surface]()

        assert _probe_record(caplog).request_id == response["X-Request-ID"]

    @pytest.mark.parametrize("surface", SURFACES)
    def test_records_carry_the_door_the_request_came_through(
        self, call: dict[str, Call], surface: str, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger=PROBE_LOGGER):
            call[surface]()

        assert _probe_record(caplog).request_source == "web"

    def test_records_outside_a_request_read_dashes(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger=PROBE_LOGGER):
            logging.getLogger(PROBE_LOGGER).info(PROBE_MESSAGE)

        record = _probe_record(caplog)
        assert (record.request_id, record.request_source) == ("-", "-")

    def test_the_handlers_own_5xx_line_carries_the_id_too(
        self, db: None, client: Client, caplog: pytest.LogCaptureFixture
    ) -> None:
        # ``BaseHandler.get_response`` logs 400+ responses to ``django.request``
        # after the middleware chain has returned, so the request-id binding has
        # to outlive the middleware that installed it.
        with (
            caplog.at_level(logging.ERROR, logger=REQUEST_LOGGER),
            mock.patch.object(
                redis.Redis, "ping", side_effect=redis.ConnectionError("refused")
            ),
        ):
            response = client.get("/healthz")

        assert response.status_code == 503
        record = _only_record(caplog, REQUEST_LOGGER)
        assert (record.request_id, record.request_source) == (
            response["X-Request-ID"],
            "web",
        )

    def test_a_request_leaves_no_context_behind_it(
        self, call: dict[str, Call], caplog: pytest.LogCaptureFixture
    ) -> None:
        # Web workers are pooled threads, so an id that is only ever set would
        # outlive its request and mislabel the next line the thread writes.
        call["internal api"]()
        caplog.clear()

        with caplog.at_level(logging.INFO, logger=PROBE_LOGGER):
            logging.getLogger(PROBE_LOGGER).info(PROBE_MESSAGE)

        record = _probe_record(caplog)
        assert (record.request_id, record.request_source) == ("-", "-")


@pytest.mark.django_db
class TestMiddlewarePlacement:
    @pytest.fixture
    def unknown_host(self, probed: None) -> Callable[[], HttpResponse]:
        return lambda: Client(headers={"host": UNKNOWN_HOST}).get("/")

    def test_a_response_produced_by_middleware_carries_the_header(
        self, unknown_host: Callable[[], HttpResponse]
    ) -> None:
        response = unknown_host()

        assert response.status_code == 400
        assert REQUEST_ID.match(response["X-Request-ID"])

    def test_the_line_that_rejects_the_request_carries_the_same_id(
        self,
        unknown_host: Callable[[], HttpResponse],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.ERROR, logger=DISALLOWED_HOST_LOGGER):
            response = unknown_host()

        record = _only_record(caplog, DISALLOWED_HOST_LOGGER)
        assert (record.request_id, record.request_source) == (
            response["X-Request-ID"],
            "web",
        )


@pytest.mark.django_db
class TestSentryTags:
    def test_an_event_carries_the_id_the_caller_was_given(
        self, client: Client, sentry: CapturingTransport
    ) -> None:
        client.raise_request_exception = False
        with override_settings(ROOT_URLCONF=__name__):
            response = client.get("/boom")

        flush_sentry()
        tags = sentry.event_with("request context boom")["tags"]
        assert tags["request_id"] == response["X-Request-ID"]
        assert tags["request_source"] == "web"


class TestBound:
    def test_records_inside_the_block_carry_the_given_id_and_source(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with (
            caplog.at_level(logging.INFO, logger=PROBE_LOGGER),
            bound("job-1", "worker"),
        ):
            logging.getLogger(PROBE_LOGGER).info(PROBE_MESSAGE)

        record = _probe_record(caplog)
        assert (record.request_id, record.request_source) == ("job-1", "worker")

    def test_records_after_the_block_read_dashes(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with bound("job-1", "worker"):
            pass

        with caplog.at_level(logging.INFO, logger=PROBE_LOGGER):
            logging.getLogger(PROBE_LOGGER).info(PROBE_MESSAGE)

        record = _probe_record(caplog)
        assert (record.request_id, record.request_source) == ("-", "-")

    def test_the_tags_come_off_with_the_block(self, sentry: CapturingTransport) -> None:
        with bound("job-1", "worker"):
            sentry_sdk.capture_exception(RuntimeError("inside boom"))
        sentry_sdk.capture_exception(RuntimeError("after boom"))

        flush_sentry()
        inside = sentry.event_with("inside boom")["tags"]
        assert (inside["request_id"], inside["request_source"]) == ("job-1", "worker")
        after = sentry.event_with("after boom").get("tags", {})
        assert after.get("request_id") != "job-1"


class TestLoggingWiring:
    """The behaviour tests above cover what leaves the process. These three lines
    are the wiring those tests depend on, named so a reshuffle says why it broke."""

    def test_the_middleware_runs_first(self) -> None:
        assert settings.MIDDLEWARE[0] == "core.request_context.RequestContextMiddleware"

    def test_the_filter_is_on_the_console_handler(self) -> None:
        assert settings.LOGGING["handlers"]["console"]["filters"] == ["request_context"]
        assert settings.LOGGING["filters"]["request_context"] == {
            "()": "core.request_context.RequestContextFilter"
        }

    def test_the_formatter_prints_both_fields(self) -> None:
        assert settings.LOGGING["formatters"]["console"]["format"] == (
            "%(asctime)s %(levelname)s "
            "[%(request_id)s %(request_source)s] %(name)s %(message)s"
        )
