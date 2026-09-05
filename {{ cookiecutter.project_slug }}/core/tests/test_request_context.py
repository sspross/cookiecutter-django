import asyncio
import contextvars
import logging
import re
from collections.abc import Callable
from typing import Any
from unittest import mock

import pytest
import redis
import sentry_sdk
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import path
from pytest_django.fixtures import Settings

from api_keys.tests.factories import UserFactory
from core.asgi import application as asgi_application
from core.request_context import bound
from core.tests.probes import PROBE_MESSAGE
from core.tests.sentry_capture import CapturingTransport, flush_sentry
from core.wsgi import application as wsgi_application

REQUEST_ID = re.compile(r"\A[0-9a-f]{32}\Z")

PROBE_LOGGER = "core.tests.probes"
CLOSE_PROBE_MESSAGE = "response close probe"

REQUEST_LOGGER = "django.request"
DISALLOWED_HOST_LOGGER = "django.security.DisallowedHost"

# In neither ``ALLOWED_HOSTS`` nor the test runner's own additions to it, so
# reading it raises ``DisallowedHost`` inside the middleware stack.
UNKNOWN_HOST = "not-an-allowed-host.example.com"

SURFACES = ("spa page", "internal api", "healthz", "admin")

type Call = Callable[..., HttpResponse]


def boom(request: HttpRequest) -> HttpResponse:
    raise RuntimeError("request context boom")


class ClosingProbeResponse(HttpResponse):
    def close(self) -> None:
        logging.getLogger(PROBE_LOGGER).info(CLOSE_PROBE_MESSAGE)
        super().close()


def closing_probe(request: HttpRequest) -> HttpResponse:
    return ClosingProbeResponse("ok")


urlpatterns = [path("boom", boom), path("closing-probe", closing_probe)]


async def asgi_get(path: str) -> dict[str, str]:
    """Drives the real ``ASGIHandler`` (``AsyncClient`` bypasses ``handle()``,
    where the response is closed from the parent task) and returns the response
    headers."""

    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"localhost")],
        "client": ("127.0.0.1", 12345),
        "server": ("localhost", 80),
    }
    body_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        # The disconnect listener waits here until the handler cancels it.
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    sent: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await asgi_application(scope, receive, send)
    (start,) = [message for message in sent if message["type"] == "http.response.start"]
    assert start["status"] == 200
    return {name.decode().lower(): value.decode() for name, value in start["headers"]}


def serve_wsgi(path: str) -> tuple[HttpResponse, dict[str, str]]:
    """Sends the body, as a WSGI server does before it closes the response."""

    # Not ``get_wsgi_application()``: that re-runs ``django.setup()``, whose logging
    # ``dictConfig`` replaces the root handlers and takes caplog's with it.
    environ = RequestFactory(headers={"host": "localhost"}).get(path).environ
    headers: dict[str, str] = {}

    def start_response(status: str, response_headers: list[tuple[str, str]]) -> None:
        assert status == "200 OK"
        headers.update({name.lower(): value for name, value in response_headers})

    response = wsgi_application(environ, start_response)
    b"".join(response)
    return response, headers


def wsgi_get(path: str) -> dict[str, str]:
    response, headers = serve_wsgi(path)
    response.close()
    return headers


def wsgi_get_closed_elsewhere(path: str) -> dict[str, str]:
    """The close-from-a-foreign-context case without Django's ASGI machinery in
    the way: served in a context of its own, as on a server thread, and closed
    from one that never carried the binding."""

    headers: dict[str, str] = {}

    def serve() -> None:
        response, served_headers = serve_wsgi(path)
        headers.update(served_headers)
        contextvars.Context().run(response.close)

    contextvars.copy_context().run(serve)
    return headers


def _healthz(client: Client, **extra: str) -> HttpResponse:
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
class TestResponseClose:
    """A response's ``close()`` runs after the handler has returned the response,
    so anything it logs is the last chance for a line to carry the request id."""

    def _records(
        self, caplog: pytest.LogCaptureFixture, message: str
    ) -> list[logging.LogRecord]:
        return [
            record
            for record in caplog.records
            if record.name == PROBE_LOGGER and record.getMessage() == message
        ]

    @pytest.mark.parametrize(
        "get",
        [
            pytest.param(lambda path: asyncio.run(asgi_get(path)), id="asgi"),
            pytest.param(wsgi_get, id="wsgi"),
            pytest.param(wsgi_get_closed_elsewhere, id="wsgi-closed-elsewhere"),
        ],
    )
    def test_the_close_line_carries_the_id(
        self,
        get: Callable[[str], dict[str, str]],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with (
            caplog.at_level(logging.INFO, logger=PROBE_LOGGER),
            override_settings(ROOT_URLCONF=__name__),
        ):
            headers = get("/closing-probe")

        (record,) = self._records(caplog, CLOSE_PROBE_MESSAGE)
        assert (record.request_id, record.request_source) == (
            headers["x-request-id"],
            "web",
        )

    def test_the_line_after_a_wsgi_close_reads_dashes(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # WSGI only: the pooled thread that served the request is the one that
        # writes the next line. An ASGI request never binds the caller's context.
        with (
            caplog.at_level(logging.INFO, logger=PROBE_LOGGER),
            override_settings(ROOT_URLCONF=__name__),
        ):
            wsgi_get("/closing-probe")
            logging.getLogger(PROBE_LOGGER).info(PROBE_MESSAGE)

        (record,) = self._records(caplog, PROBE_MESSAGE)
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
        sentry_sdk.capture_exception(RuntimeError("before boom"))
        with bound("job-1", "worker"):
            sentry_sdk.capture_exception(RuntimeError("inside boom"))
        sentry_sdk.capture_exception(RuntimeError("after boom"))

        flush_sentry()
        inside = sentry.event_with("inside boom")["tags"]
        assert (inside["request_id"], inside["request_source"]) == ("job-1", "worker")
        before = sentry.event_with("before boom").get("tags", {})
        after = sentry.event_with("after boom").get("tags", {})
        assert after == before

    def test_an_exception_that_leaves_the_block_is_reported_with_its_tags(
        self, sentry: CapturingTransport
    ) -> None:
        # Whoever reports it runs after the block: RQ's exception handler for a
        # job, the excepthook for a command. Outside a worker here, so the proof
        # is about the exception, not about RQ's per-job scope.
        try:
            with bound("job-1", "worker"):
                raise RuntimeError("escaped boom")
        except RuntimeError as escaped:
            sentry_sdk.capture_exception(escaped)
        sentry_sdk.capture_exception(RuntimeError("after boom"))

        flush_sentry()
        escaped_tags = sentry.event_with("escaped boom")["tags"]
        assert (escaped_tags["request_id"], escaped_tags["request_source"]) == (
            "job-1",
            "worker",
        )
        after_tags = sentry.event_with("after boom").get("tags", {})
        assert "request_id" not in after_tags
        assert "request_source" not in after_tags


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
