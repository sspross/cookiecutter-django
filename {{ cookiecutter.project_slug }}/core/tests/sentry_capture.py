from typing import Any

import sentry_sdk
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

# Parses, but the host deliberately does not resolve: the backstop for anything
# that initializes the real SDK without one of our transports.
TEST_DSN = "https://public@sentry.invalid/1"

type Payload = dict[str, Any]


class CapturingTransport(Transport):
    def __init__(self) -> None:
        super().__init__()
        self.envelopes: list[Envelope] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        self.envelopes.append(envelope)

    def items(self) -> list[tuple[str, Payload]]:
        return [
            (item.type, item.payload.json or {})
            for envelope in self.envelopes
            for item in envelope.items
        ]

    def item_types(self) -> list[str]:
        return [item_type for item_type, _ in self.items()]

    def events(self) -> list[Payload]:
        return [payload for item_type, payload in self.items() if item_type == "event"]

    def _exception_values(self) -> list[tuple[Payload, str | None]]:
        return [
            (payload, exception.get("value"))
            for payload in self.events()
            for exception in payload.get("exception", {}).get("values", [])
        ]

    def event_messages(self) -> list[str | None]:
        return [message for _, message in self._exception_values()]

    def event_with(self, exception_value: str) -> Payload:
        matches = [
            payload
            for payload, message in self._exception_values()
            if message == exception_value
        ]
        assert len(matches) == 1, f"expected one {exception_value!r} event, {matches}"
        return matches[0]

    def logs(self) -> list[Payload]:
        # Sentry's log protocol wraps attribute values in ``{"value", "type"}``
        # envelopes, and ``level`` is OTel severity text (``logging.WARNING``
        # reads back as ``"warn"``).
        return [
            {
                "level": entry.get("level"),
                "body": entry.get("body"),
                "attributes": {
                    name: attribute.get("value")
                    for name, attribute in entry.get("attributes", {}).items()
                },
            }
            for item_type, payload in self.items()
            if item_type == "log"
            for entry in payload.get("items", [])
        ]

    def log_bodies(self) -> list[str | None]:
        return [entry["body"] for entry in self.logs()]


def flush_sentry() -> None:
    sentry_sdk.get_client().flush()
