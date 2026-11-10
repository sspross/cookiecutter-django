import logging
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from typing import Any

import sentry_sdk
from django.core.signals import request_finished
from django.http import HttpRequest, HttpResponse

__all__ = [
    "REQUEST_ID_HEADER",
    "UNSET",
    "RequestContextFilter",
    "RequestContextMiddleware",
    "bound",
    "classify_source",
    "request_id",
    "request_source",
    "tag_event_from_exception",
]

UNSET = "-"

REQUEST_ID_HEADER = "X-Request-ID"

SOURCE_WEB = "web"

# Ships empty; see GLOSSARY.md "Observability" for what a second entry buys.
EXTERNAL_SOURCES: tuple[tuple[str, str], ...] = ()

request_id: ContextVar[str] = ContextVar("request_id", default=UNSET)

request_source: ContextVar[str] = ContextVar("request_source", default=UNSET)

# Set by the middleware alone, so a response closing inside a ``bound()`` block
# cannot undo that block's binding.
_request_bound: ContextVar[bool] = ContextVar("request_bound", default=False)

_CARRIED = "_request_context"


def classify_source(path: str) -> str:
    for prefix, source in EXTERNAL_SOURCES:
        if path.startswith(prefix):
            return source
    return SOURCE_WEB


def _bind(new_request_id: str, new_request_source: str) -> None:
    # Set, never reset through a token, which is only valid in the context that
    # created it; see :func:`_closing_in_request_context`.
    request_id.set(new_request_id)
    request_source.set(new_request_source)


def _tag(scope: sentry_sdk.Scope, new_request_id: str, new_request_source: str) -> None:
    scope.set_tag("request_id", new_request_id)
    scope.set_tag("request_source", new_request_source)


@contextmanager
def bound(new_request_id: str, new_request_source: str) -> Iterator[None]:
    previous = (request_id.get(), request_source.get())
    with sentry_sdk.new_scope() as scope:
        _bind(new_request_id, new_request_source)
        _tag(scope, new_request_id, new_request_source)
        try:
            yield
        except BaseException as exception:
            # Reported after the block exits (by RQ's ``handle_exception`` for a job),
            # so the exception carries the pair to the event that reports it.
            setattr(exception, _CARRIED, (new_request_id, new_request_source))
            raise
        finally:
            _bind(*previous)


def tag_event_from_exception(
    event: dict[str, Any], hint: dict[str, Any]
) -> dict[str, Any]:
    exception = hint.get("exc_info", (None, None, None))[1]
    carried = getattr(exception, _CARRIED, None)
    if carried is not None:
        event.setdefault("tags", {}).update(
            request_id=carried[0], request_source=carried[1]
        )
    return event


class RequestContextMiddleware:
    """The binding outlives this middleware: ``BaseHandler.get_response`` logs responses
    of 400 and above after the chain returns. ``_unbind_on_response_close`` ends it."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if _request_bound.get():
            # Defensive: an earlier response on this context was never closed.
            _unbind_request()
        # Never the inbound X-Request-ID: a client could collide unrelated requests
        # onto one id.
        generated = uuid.uuid4().hex
        source = classify_source(request.path)
        # The isolation scope, which ``DjangoIntegration`` gives each request one
        # of, so a tag cannot leak into the next request's events.
        _tag(sentry_sdk.get_isolation_scope(), generated, source)
        _request_bound.set(True)
        _bind(generated, source)
        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = generated
        response.close = _closing_in_request_context(  # type: ignore[method-assign]
            response.close
        )
        return response


def _closing_in_request_context(close: Callable[[], None]) -> Callable[[], None]:
    """``ASGIHandler`` closes from a parent task, whose context may lack the binding.
    WSGI closes in the request's context, where a copy would leave the thread bound."""

    request_context = copy_context()

    def close_in_request_context() -> None:
        if _request_bound.get():
            close()
        else:
            request_context.run(close)

    return close_in_request_context


def _unbind_request() -> None:
    _request_bound.set(False)
    _bind(UNSET, UNSET)


def _unbind_on_response_close(**_kwargs: object) -> None:
    """Undoes the binding on response close, because under WSGI a pooled thread serves
    the next request."""

    if _request_bound.get():
        _unbind_request()


request_finished.connect(
    _unbind_on_response_close, dispatch_uid="core.request_context.unbind"
)


class RequestContextFilter(logging.Filter):
    """A filter, not a formatter change: Sentry Logs indexes record attributes. On the
    console handler because the SDK's hook runs after it and reads that record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        record.request_source = request_source.get()
        return True
