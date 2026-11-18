from collections.abc import Iterator

import pytest
import sentry_sdk

from core.observability import sentry_options
from core.tests.sentry_capture import UNRESOLVABLE_TEST_DSN, CapturingTransport


@pytest.fixture(autouse=True)
def _sentry_scopes_forked_per_test() -> Iterator[None]:
    with sentry_sdk.isolation_scope():
        yield


@pytest.fixture
def sentry() -> Iterator[CapturingTransport]:
    transport = CapturingTransport()
    client = sentry_sdk.Client(
        **sentry_options(UNRESOLVABLE_TEST_DSN, "test"), transport=transport
    )
    scope = sentry_sdk.get_global_scope()
    previous = scope.client
    scope.set_client(client)
    try:
        yield transport
    finally:
        client.close()
        scope.set_client(previous)
