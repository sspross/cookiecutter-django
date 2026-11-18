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

EXTERNAL_SOURCES: tuple[tuple[str, str], ...] = ()

request_id: ContextVar[str] = ContextVar("request_id", default=UNSET)

request_source: ContextVar[str] = ContextVar("request_source", default=UNSET)

_bound_by_middleware: ContextVar[bool] = ContextVar(
    "bound_by_middleware", default=False
)

_CARRIED = "_request_context"


def classify_source(path: str) -> str:
    for prefix, source in EXTERNAL_SOURCES:
        if path.startswith(prefix):
            return source
    return SOURCE_WEB


def _bind(new_request_id: str, new_request_source: str) -> None:
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
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        _unbind_if_bound_by_middleware()
        generated = uuid.uuid4().hex
        source = classify_source(request.path)
        _tag(sentry_sdk.get_isolation_scope(), generated, source)
        _bound_by_middleware.set(True)
        _bind(generated, source)
        response = self.get_response(request)
        response[REQUEST_ID_HEADER] = generated
        response.close = _closing_in_request_context(  # type: ignore[method-assign]
            response.close
        )
        return response


def _closing_in_request_context(close: Callable[[], None]) -> Callable[[], None]:
    request_context = copy_context()

    def close_in_request_context() -> None:
        if _bound_by_middleware.get():
            close()
        else:
            request_context.run(close)

    return close_in_request_context


def _unbind_request() -> None:
    _bound_by_middleware.set(False)
    _bind(UNSET, UNSET)


def _unbind_if_bound_by_middleware() -> None:
    if _bound_by_middleware.get():
        _unbind_request()


def _unbind_on_response_close(**_kwargs: object) -> None:
    _unbind_if_bound_by_middleware()


request_finished.connect(
    _unbind_on_response_close, dispatch_uid="core.request_context.unbind"
)


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        record.request_source = request_source.get()
        return True
