import logging
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

PROBE_MESSAGE = "request context probe"


class LoggingProbeMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        logger.info(PROBE_MESSAGE)
        return self.get_response(request)
