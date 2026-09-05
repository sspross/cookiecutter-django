"""The request id and request source every log line and event carries.

ContextVar rather than a thread-local, which an ASGI worker would share across
the requests it interleaves on one thread. Hand-rolled because django-guid and
its peers propagate to Celery only.

Generated, never read from an inbound ``X-Request-ID``: that header is
client-controlled, and honouring it would let a caller collide unrelated
requests onto a single id.
"""

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

# Ships empty; see CONTEXT.md "Observability" for what a second entry buys.
EXTERNAL_SOURCES: tuple[tuple[str, str], ...] = ()

request_id: ContextVar[str] = ContextVar("request_id", default=UNSET)

request_source: ContextVar[str] = ContextVar("request_source", default=UNSET)

# Set by the middleware alone, so a response closing inside a ``bound()`` block
# cannot undo that block's binding.
_request_bound: ContextVar[bool] = ContextVar("request_bound", default=False)

# The attribute :func:`bound` leaves on an exception that escapes its block.
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
    """For work whose extent really is a block, such as a worker job. A request's
    binding is not a block; see :class:`RequestContextMiddleware`.

    The tags go on a forked current scope and come off with the block. An
    exception that leaves the block is reported after it (by RQ's
    ``handle_exception`` for a job), so the exception carries the pair itself and
    :func:`tag_event_from_exception` puts it on the event that reports it. Nothing
    is left on a scope the next job or command would inherit."""

    previous = (request_id.get(), request_source.get())
    with sentry_sdk.new_scope() as scope:
        _bind(new_request_id, new_request_source)
        _tag(scope, new_request_id, new_request_source)
        try:
            yield
        except BaseException as exception:
            setattr(exception, _CARRIED, (new_request_id, new_request_source))
            raise
        finally:
            _bind(*previous)


def tag_event_from_exception(
    event: dict[str, Any], hint: dict[str, Any]
) -> dict[str, Any]:
    """``before_send`` in :func:`core.observability.sentry_options`."""

    exception = hint.get("exc_info", (None, None, None))[1]
    carried = getattr(exception, _CARRIED, None)
    if carried is not None:
        event.setdefault("tags", {}).update(
            request_id=carried[0], request_source=carried[1]
        )
    return event


class RequestContextMiddleware:
    """Must be first in ``settings.MIDDLEWARE``, so a response produced by another
    middleware (the security redirect, an invalid-host 400) is correlated too. The
    binding then deliberately outlives this middleware, because
    ``BaseHandler.get_response`` logs 400-and-above responses to ``django.request``
    after the chain returns; :func:`_unbind_on_response_close` undoes it instead."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if _request_bound.get():
            # Defensive: a response that was never closed. Nothing here streams.
            _unbind_request()
        generated = uuid.uuid4().hex
        source = classify_source(request.path)
        # The isolation scope, which ``DjangoIntegration`` gives each request one
        # of, so a tag cannot leak into the next request's events.
        _tag(sentry_sdk.get_isolation_scope(), generated, source)
        _request_bound.set(True)
        _bind(generated, source)
        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = generated
        response.close = _closing_in_request_context(response.close)
        return response


def _closing_in_request_context(close: Callable[[], None]) -> Callable[[], None]:
    """Django's ``ASGIHandler`` closes the response from the parent task, whose
    context need not carry the binding the middleware made in a child. A WSGI
    server closes in the request's own context, where running a copy would leave
    the pooled thread bound; hence the check."""

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
    """``request_finished`` fires from ``HttpResponseBase.close()``. Unbinding
    matters because under WSGI a pooled thread serves the next request."""

    if _request_bound.get():
        _unbind_request()


request_finished.connect(
    _unbind_on_response_close, dispatch_uid="core.request_context.unbind"
)


class RequestContextFilter(logging.Filter):
    """A filter rather than a formatter change, because Sentry Logs indexes record
    attributes. Attached to the console handler because the SDK's hook runs after
    the handlers it patches, so the record it reads is the filtered one."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        record.request_source = request_source.get()
        return True
