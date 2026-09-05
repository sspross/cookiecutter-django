import io
import json
import logging
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any
from unittest import mock

import django_rq
import pytest
import redis
import sentry_sdk
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.http import HttpRequest, HttpResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import path
from ninja import NinjaAPI
from rq import Queue, SimpleWorker, get_current_job
from rq.job import Job
from rq.results import Result

from core.observability import (
    DEFAULT_ENVIRONMENT,
    IGNORED_LOGGERS,
    init_sentry,
    sentry_options,
)
from core.request_context import bound
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


@contextmanager
def console_output() -> Iterator[io.StringIO]:
    """Swaps the streams rather than reading captured stderr, because a handler
    holds the ``sys.stderr`` it was built with, which pytest replaced later.
    Every handler in the tree, so a record printed twice shows up as two lines;
    pytest's own handlers are left out."""

    stream = io.StringIO()
    loggers = [logging.getLogger(), *logging.getLogger().manager.loggerDict.values()]
    handlers = {
        handler
        for logger in loggers
        if isinstance(logger, logging.Logger)
        for handler in logger.handlers
        if isinstance(handler, logging.StreamHandler)
        and not type(handler).__module__.startswith("_pytest")
    }
    previous = {handler: handler.stream for handler in handlers}
    for handler in handlers:
        handler.setStream(stream)
    try:
        yield stream
    finally:
        for handler, original in previous.items():
            handler.setStream(original)


@contextmanager
def logger_at(name: str, level: int) -> Iterator[logging.Logger]:
    logger = logging.getLogger(name)
    previous = logger.level
    logger.setLevel(level)
    try:
        yield logger
    finally:
        logger.setLevel(previous)


def failing_job() -> None:
    raise RuntimeError("job boom")


def failing_bound_job() -> None:
    # The pattern OPERATIONS.md "Correlating a job" documents.
    job = get_current_job()
    assert job is not None
    with bound(job.id, "worker"):
        raise RuntimeError("bound job boom")


def perform_failing_jobs(queue_name: str, *funcs: Callable[[], None]) -> list[str]:
    # One real worker, because RQ's integration reports from
    # ``Worker.handle_exception`` alone, which the synchronous enqueue of the test
    # settings never reaches. Each caller passes its own queue name so tests share
    # no Redis keys.
    connection = django_rq.get_connection()
    queue = Queue(queue_name, connection=connection)
    jobs = [
        Job.create(func=func, connection=connection, origin=queue.name)
        for func in funcs
    ]
    worker = SimpleWorker([queue], connection=connection)
    try:
        for job in jobs:
            job.save()
            worker.perform_job(job, queue)
    finally:
        # Redis is real here (pytest-django's rollback covers SQL only) and a
        # failed job carries RQ's default one-year failure_ttl, so without this
        # every suite run leaks job, result, registry and worker keys.
        for job in jobs:
            Result.delete_all(job)
            job.delete()
        worker.register_death()
        connection.delete(worker.key, queue.failed_job_registry.key)
        queue.delete()
    return [job.id for job in jobs]


def run_failing_job(queue_name: str) -> str:
    return perform_failing_jobs(queue_name, failing_job)[0]


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

    def test_the_options_carry_the_django_rq_and_logging_integrations(self) -> None:
        integrations = {
            type(integration).__name__
            for integration in sentry_options(TEST_DSN, "test")["integrations"]
        }
        assert {"DjangoIntegration", "RqIntegration", "LoggingIntegration"} <= (
            integrations
        )

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

    def test_an_unhandled_job_exception_becomes_an_event(
        self, sentry: CapturingTransport
    ) -> None:
        job_id = run_failing_job("observability-test")
        flush_sentry()
        assert len(sentry.events()) == 1
        event = sentry.event_with("job boom")
        assert event["extra"]["rq-job"]["job_id"] == job_id

    def test_a_failing_job_leaves_no_redis_keys_behind(self) -> None:
        connection = django_rq.get_connection()
        before = set(connection.keys("rq:*"))
        run_failing_job("observability-test-cleanup")
        assert set(connection.keys("rq:*")) == before

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
class TestJobCorrelation:
    def test_a_job_that_raises_inside_bound_produces_a_correlated_event(
        self, sentry: CapturingTransport
    ) -> None:
        # The block has already unwound when RQ reports the failure, so the
        # tags must outlive it by exactly the job.
        (job_id,) = perform_failing_jobs("observability-test-bound", failing_bound_job)
        flush_sentry()
        tags = sentry.event_with("bound job boom")["tags"]
        assert (tags["request_id"], tags["request_source"]) == (job_id, "worker")

    def test_the_next_job_on_the_same_worker_carries_no_tags(
        self, sentry: CapturingTransport
    ) -> None:
        perform_failing_jobs(
            "observability-test-bound-next", failing_bound_job, failing_job
        )
        flush_sentry()
        assert len(sentry.events()) == 2
        tags = sentry.event_with("job boom").get("tags", {})
        assert "request_id" not in tags
        assert "request_source" not in tags


class TestLevelPolicy:
    def test_an_application_info_log_ships(self, sentry: CapturingTransport) -> None:
        logging.getLogger("core.services").info("core says hello")
        logging.getLogger("api_keys.services").info("key issued")
        logging.getLogger("users.services").info("user signed up")
        flush_sentry()
        assert "core says hello" in sentry.log_bodies()
        assert "key issued" in sentry.log_bodies()
        assert "user signed up" in sentry.log_bodies()

    def test_a_third_party_info_log_does_not_ship(
        self, sentry: CapturingTransport
    ) -> None:
        logging.getLogger("django.db.models").info("django chatter")
        logging.getLogger("rq.queue").info("rq chatter")
        flush_sentry()
        assert sentry.log_bodies() == []

    def test_a_third_party_warning_ships(self, sentry: CapturingTransport) -> None:
        logging.getLogger("django.db.models").warning("django is unhappy")
        flush_sentry()
        assert "django is unhappy" in sentry.log_bodies()

    def test_lowering_a_logger_ships_what_it_lets_through(
        self, sentry: CapturingTransport
    ) -> None:
        with logger_at("core.services", logging.DEBUG) as logger:
            logger.debug("cache warmed")
            flush_sentry()
        assert "cache warmed" in sentry.log_bodies()

    def test_the_console_handler_stays_on_root(self) -> None:
        assert "console" in settings.LOGGING["handlers"]
        assert settings.LOGGING["root"]["handlers"] == ["console"]

    def test_every_record_prints_once(self) -> None:
        with console_output() as printed:
            logging.getLogger("django.db.models").warning("django is unhappy")
            logging.getLogger("django.request").error("Internal Server Error: /boom")
            logging.getLogger("core.services").info("core says hello")
        lines = printed.getvalue().splitlines()
        assert len(lines) == 3
        assert lines[0].endswith("django is unhappy")
        assert lines[1].endswith("Internal Server Error: /boom")
        assert lines[2].endswith("core says hello")


class TestIgnoredLoggers:
    def test_a_scanner_404_ships_to_neither_sink(
        self, sentry: CapturingTransport
    ) -> None:
        with console_output() as printed:
            logging.getLogger("django.request").warning("Not Found: /.env")
            flush_sentry()
        assert sentry.log_bodies() == []
        assert printed.getvalue() == ""

    def test_a_request_error_still_ships(self, sentry: CapturingTransport) -> None:
        with console_output() as printed:
            logging.getLogger("django.request").error("Internal Server Error: /boom")
            flush_sentry()
        assert "Internal Server Error: /boom" in sentry.log_bodies()
        assert printed.getvalue().count("Internal Server Error: /boom") == 1

    @pytest.mark.parametrize("name", IGNORED_LOGGERS)
    def test_a_muted_logger_prints_but_ships_no_sentry_item(
        self, name: str, sentry: CapturingTransport
    ) -> None:
        with console_output() as printed:
            logging.getLogger(name).error("Invalid HTTP_HOST header: '203.0.113.10'.")
            flush_sentry()
        assert sentry.item_types() == []
        assert printed.getvalue().count("Invalid HTTP_HOST header:") == 1

    @pytest.mark.parametrize("name", ["rq.worker", "rq.scheduler", "rq.job"])
    @pytest.mark.parametrize("level", [logging.INFO, logging.WARNING])
    def test_rq_chatter_does_not_ship_even_when_rq_lowers_the_logger(
        self, name: str, level: int, sentry: CapturingTransport
    ) -> None:
        with logger_at(name, logging.INFO) as logger, console_output() as printed:
            logger.log(level, "Listening on default")
            flush_sentry()
        assert sentry.item_types() == []
        assert printed.getvalue().count("Listening on default") == 1

    def test_a_muted_rq_worker_still_reports_an_unhandled_job_exception(
        self, sentry: CapturingTransport
    ) -> None:
        with logger_at("rq.worker", logging.INFO):
            job_id = run_failing_job("observability-test-muted")
            flush_sentry()
        event = sentry.event_with("job boom")
        assert event["extra"]["rq-job"]["job_id"] == job_id
        assert sentry.log_bodies() == []


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
        with mock.patch.object(redis.Redis, "ping", return_value=True):
            response = application(
                environ, lambda status, headers: statuses.append(status)
            )
            body = b"".join(response)
            # What a WSGI server does after the body; it fires request_finished,
            # which is what unbinds the request context.
            response.close()
        assert statuses == ["200 OK"]
        assert json.loads(body) == {"database": "ok", "redis": "ok"}

        flush_sentry()
        assert sentry.item_types() == []
