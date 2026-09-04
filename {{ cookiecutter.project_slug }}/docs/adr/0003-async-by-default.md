# 0003 — Async runtime ships by default

## Context

Most Django projects spawned from this template will eventually need
background work: an outbound LLM call, a long-running export, a webhook
fan-out, an email send. Django's async views do not cover this — they solve
concurrency, not deferred work; a long-running outbound call still wants to
live off the request thread. Retrofitting an async runtime later is more
painful than carrying it from day one — it touches `INSTALLED_APPS`,
settings, Dockerfile, deployment manifest, and CI shape.

The template ships *infrastructure* for async work, not jobs. There are
no actual `@job`-decorated functions in the generated project — only the
RQ + Redis wiring that lets a developer add one in five minutes.

## Decision

The template ships:

- `django-rq` in `INSTALLED_APPS` and `RQ_QUEUES` configured against
  `REDIS_URL`. RQ over Celery: one broker shape instead of Celery's
  broker-plus-result-backend, which keeps the mental model small.
- A `redis` backing service in both deployment manifests: Appliku's managed
  Redis in `appliku.yml`, the `redis:7` service in `compose.yaml`.
- `worker.sh` script: `uv run python manage.py rqworker default` — the
  *forking* worker (prod, Linux). Local dev uses `make worker.dev`, which
  runs the same queue with `--worker-class rq.worker.SimpleWorker`
  (in-process, no `os.fork()` — fork-safe on macOS). Write jobs correct
  under **both**: don't rely on in-process state surviving between jobs,
  and don't rely on SimpleWorker's lack of a hard per-job timeout — prod's
  forking worker enforces `RQ_QUEUES` `DEFAULT_TIMEOUT` and kills the job.
- A `worker` process in both deployment manifests, built from the same image as
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
`.delay(...)`. Tests can flip async off by overriding the queue's
`ASYNC` setting; Redis is still required at enqueue time for Job
persistence.

## Consequences

Positive:

- Adding a background job is a single-file change, not a refactor.
- The local-dev topology matches production: `make worker.dev` against
  a local `redis-server` runs the same web + worker + redis shape that the
  deployment target runs.
- Test suites that need inline execution have one knob to flip.

Negative:

- A Redis dependency for projects that may never need it. It is *not*
  needed for `runserver` or ordinary requests — RQ connects to Redis
  lazily, only when the worker runs or a job is enqueued, and a freshly
  generated project has no jobs. So Redis is optional until the first
  job; once you have one, `make worker.dev` (and any `.delay()`) needs
  `redis-server` running locally.
- A few extra lines in the Dockerfile and in both deployment manifests that
  some generated projects will never use.

These costs are real but small, and the alternative is discovering you
need async on week 6 and bolting it on across five files.
