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
from contextvars import ContextVar, Token

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
]

UNSET = "-"

REQUEST_ID_HEADER = "X-Request-ID"

SOURCE_WEB = "web"

# Empty on purpose: every path a generated project ships reads `web`. A second
# API surface per audience (the growth path in ADR-0002) adds one tuple here and
# touches nothing else.
EXTERNAL_SOURCES: tuple[tuple[str, str], ...] = ()

request_id: ContextVar[str] = ContextVar("request_id")

request_source: ContextVar[str] = ContextVar("request_source")

Binding = tuple[Token[str], Token[str]]

_binding: ContextVar[Binding | None] = ContextVar("request_binding", default=None)


def classify_source(path: str) -> str:
    for prefix, source in EXTERNAL_SOURCES:
        if path.startswith(prefix):
            return source
    return SOURCE_WEB


def _bind(new_request_id: str, new_request_source: str) -> Binding:
    """The tags go on the isolation scope, which ``DjangoIntegration`` gives each
    request one of, so a tag cannot leak into the next request's events."""

    sentry_sdk.get_isolation_scope().set_tag("request_id", new_request_id)
    sentry_sdk.get_isolation_scope().set_tag("request_source", new_request_source)
    return (request_id.set(new_request_id), request_source.set(new_request_source))


def _unbind(binding: Binding) -> None:
    request_id.reset(binding[0])
    request_source.reset(binding[1])


@contextmanager
def bound(new_request_id: str, new_request_source: str) -> Iterator[None]:
    """For work whose extent really is a block, such as a worker job. A request's
    binding is not a block; see :class:`RequestContextMiddleware`."""

    binding = _bind(new_request_id, new_request_source)
    try:
        yield
    finally:
        _unbind(binding)


class RequestContextMiddleware:
    """Must be first in ``settings.MIDDLEWARE``, so a response produced by another
    middleware (the security redirect, an invalid-host 400) is correlated too. The
    binding then deliberately outlives this middleware, because
    ``BaseHandler.get_response`` logs 400-and-above responses to ``django.request``
    after the chain returns; :func:`_unbind_on_response_close` undoes it instead."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        stale = _binding.get()
        if stale is not None:
            # Defensive: a response that was never closed. Nothing here streams.
            _unbind(stale)
        generated = uuid.uuid4().hex
        _binding.set(_bind(generated, classify_source(request.path)))
        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = generated
        return response


def _unbind_on_response_close(**_kwargs: object) -> None:
    """``request_finished`` fires from ``HttpResponseBase.close()``, in the request's
    own thread and context, which is what makes the middleware's reset tokens valid
    here. Resetting matters because a pooled thread serves the next request."""

    binding = _binding.get()
    if binding is None:
        return
    _binding.set(None)
    _unbind(binding)


request_finished.connect(
    _unbind_on_response_close, dispatch_uid="core.request_context.unbind"
)


class RequestContextFilter(logging.Filter):
    """A filter rather than a formatter change, because Sentry Logs indexes record
    attributes. Attached to the console handler because the SDK's hook runs after
    the handlers it patches, so the record it reads is the filtered one."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get(UNSET)
        record.request_source = request_source.get(UNSET)
        return True
