# 0003 — Async runtime ships by default

## Context

Most Django projects spawned from this template will eventually need
background work: an outbound LLM call, a long-running export, a webhook
fan-out, an email send. Django's async views do not cover this — they solve
concurrency, not deferred work; a long-running outbound call still wants to
live off the request thread. Retrofitting an async runtime later is more
painful than carrying it from day one: it touches `INSTALLED_APPS`,
settings, the deployment manifests, and CI shape.

The template ships *infrastructure* for async work, not jobs. There are
no actual `@job`-decorated functions in the generated project — only the
RQ + Redis wiring that lets a developer add one in five minutes.

## Decision

The template ships:

- `django-rq` in `INSTALLED_APPS` and `RQ_QUEUES` configured against
  `REDIS_URL`. RQ over Celery: one broker shape instead of Celery's
  broker-plus-result-backend, which keeps the mental model small.
- A `redis` backing service in every deployment manifest: Appliku's managed
  Redis in `appliku.yml`, the `redis:7` service in `compose.yaml` and
  `compose.prod.yaml`.
- `worker.sh` script: `uv run python manage.py rqworker default` — the
  *forking* worker. It runs in production and in the local compose stack
  (`make up`), both in Linux containers, so macOS never forks. It raises
  `JobTimeoutException` inside a job that outruns `RQ_QUEUES`
  `DEFAULT_TIMEOUT` and kills one that is still running 60 seconds later.
- A `worker` process in every deployment manifest, built from the same image as
  `web`, running `./worker.sh` instead of `./web.sh`.
- The django-rq dashboard mounted at `/django-rq/` (gated to staff by
  django-rq itself).

Scheduling is off by default. `worker.sh` runs `rqworker default` without
`--with-scheduler`, so a delayed job (`enqueue_in()`, `enqueue_at()`) is
persisted but never moved onto the queue. Add `--with-scheduler` to `worker.sh`
the moment the project enqueues its first delayed job; that one-line change is
the whole migration. It is off until then because the flag starts a scheduler
that polls Redis on an interval for the lifetime of every worker, and a freshly
generated project has no delayed jobs for it to find. Leaving it on by default
would mean the shipped default is a moving part nobody in a new project can
observe or reason about.

The first job a developer writes goes in `<their_app>/jobs.py`,
decorated with `@django_rq.job("default")`, and is enqueued via
`.delay(...)`. `core/settings/test.py` sets the queue's `ASYNC` to
`False`, so `.delay()` runs inline in tests; Redis is still required at
enqueue time for Job persistence. A job runs outside any request, so wrap its body in `bound()`
from `core/request_context.py` to give its log lines and Sentry items a
request id and source; see "Correlating a job" in `docs/OPERATIONS.md`.

## Consequences

Positive:

- Adding a background job is a single-file change, not a refactor.
- The local topology matches production: `make up` runs the same web + worker
  + redis shape that the deployment target runs, from the same image.

Negative:

- A Redis dependency, including for projects that never write a job.
  It is *not* needed for most requests: RQ connects
  to Redis lazily, only when the worker runs or a job is enqueued.
  `POST /api/api-keys/` does need it, because its throttle counters live
  in the Redis cache, and `/healthz` answers 503 without it.
  `make test` does need it from the start, because the observability
  suite runs a real worker against a real queue, and so does any `.delay()`.
- A few extra lines in every deployment manifest that some generated
  projects will never use.
