# Sentry error events are unexpected behaviour only

A Sentry error event means an unhandled exception, reported by an SDK
integration (`DjangoIntegration` for web requests, `RqIntegration` for jobs).
The app captures nothing on purpose: ruff's `TID251` bans
`sentry_sdk.capture_exception` outside tests, and the logging integration's
`event_level` is `None`, so no log line at any level becomes an event. Every
event is a candidate for an alert, so a project that captures expected
failures (a retry that gave up, a recorded third-party timeout, a validation
the caller can fix) turns the issue stream into a second log that pages
someone. The SDK's default `event_level` of ERROR would do the same with every
future `logger.error`.

An expected failure is a log line plus recorded state. Log it at the level it
deserves, with the identifying fields in `extra`, and land the outcome where
the domain keeps it (a status field, a row, a flag). The line ships to Sentry
Logs, where it is queryable next to the issue stream. Capturing the failure at
a lower severity or in a separate Sentry project changes nothing, because an
event is an event to the alerting rules. A failure no state records is a gap
in the domain model: record the state.

Alerting on expected failures is a Sentry-side rule (a Logs query, an alert on
a metric), not app code.
