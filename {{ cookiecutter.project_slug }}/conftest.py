from collections.abc import Iterator

import pytest
import sentry_sdk

from core.observability import sentry_options
from core.tests.sentry_capture import TEST_DSN, CapturingTransport


@pytest.fixture(autouse=True)
def _sentry_scopes_of_its_own() -> Iterator[None]:
    """The SDK's WSGI and ASGI handlers fork the scopes per request. The test client
    does not, so a tag set by one test's request would reach the next test."""

    with sentry_sdk.isolation_scope():
        yield


@pytest.fixture
def sentry() -> Iterator[CapturingTransport]:
    """Not ``sentry_sdk.init``: that would leave a client for the rest of the suite."""

    transport = CapturingTransport()
    client = sentry_sdk.Client(**sentry_options(TEST_DSN, "test"), transport=transport)
    scope = sentry_sdk.get_global_scope()
    previous = scope.client
    scope.set_client(client)
    try:
        yield transport
    finally:
        client.close()
        scope.set_client(previous)
