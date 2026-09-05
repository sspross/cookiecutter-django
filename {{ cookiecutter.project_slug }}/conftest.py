from collections.abc import Iterator

import pytest
import sentry_sdk

from core.observability import sentry_options
from core.tests.sentry_capture import TEST_DSN, CapturingTransport


@pytest.fixture
def sentry() -> Iterator[CapturingTransport]:
    """Deliberately not ``sentry_sdk.init``: the client is set on the global scope
    and taken off again, so a test that captures leaves no client behind for the
    rest of the suite."""

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
