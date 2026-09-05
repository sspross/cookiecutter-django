# 0007 - Sentry error events are unexpected behaviour only

## Context

The Sentry SDK is initialized whenever `SENTRY_DSN` is set (`core/observability.py`,
called from `CoreConfig.ready`). Once a DSN is present, every `sentry_sdk.capture_exception`
and every log line the logging integration is allowed to promote lands in the issue stream,
and every issue is a candidate for an alert. A project that captures expected failures
(a retry that gave up, a third-party call that timed out and was recorded, a validation
the caller can fix) turns that stream into a second log, whose only distinguishing property
is that it pages someone.

## Decision

**A Sentry error event means unexpected behaviour: an unhandled exception, reported by an
SDK integration** (`DjangoIntegration` for web requests). The app captures nothing on
purpose, and the logging integration's `event_level` is `None`, so no log line at any level
becomes an event either.

**An expected failure is a log line plus recorded state.** Log it at the level it deserves
(`logger.error`, `logger.exception`, `logger.warning`) with the identifying fields in
`extra`, and land the outcome where the domain keeps it (a status field, a row, a flag).
The log line ships to Sentry Logs, where it is queryable next to the issue stream; the
state is readable in the app, in admin and over the API.

Alerting on expected failures is a Sentry-side rule (a Logs query, an alert on a metric),
not app code.

## Consequences

- The issue stream is reserved for bugs; anything in it is worth interrupting someone for.
- Expected failures are watched where they are queryable: Sentry Logs and the recorded
  state. Adding an alert on either changes a Sentry rule, not a deploy.
- Sentry Logs retention is shorter than issue retention; the recorded state carries the
  history for as long as the rows exist.
- No `traces_sample_rate` and no session tracking: the Sentry bill is errors and logs.

## Alternatives considered

- **Capture expected failures at lower severity or on a separate project.** An event is
  an event to the alerting rules; the useful split is by whether the behaviour was expected.
- **Set the logging integration's `event_level` to ERROR.** Makes every future
  `logger.error` an alert by accident, and duplicates the line as an event and a log.
- **Capture only the failures no state records.** A failure nothing records is a gap in
  the domain model; record the state rather than page on the gap.
