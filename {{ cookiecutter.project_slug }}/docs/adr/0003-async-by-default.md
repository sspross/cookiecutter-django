# 0003 — Async runtime ships by default

Status: Accepted

## Context

Most Django projects spawned from this template will eventually need
background work: an outbound LLM call, a long-running export, a webhook
fan-out, an email send. Retrofitting an async runtime later is more
painful than carrying it from day one — it touches `INSTALLED_APPS`,
settings, Dockerfile, compose, deployment manifest, and CI shape.

The template ships *infrastructure* for async work, not jobs. There are
no actual `@job`-decorated functions in the generated project — only the
RQ + Redis wiring that lets a developer add one in five minutes.

## Decision

The template ships:

- `django-rq` in `INSTALLED_APPS` and `RQ_QUEUES` configured against
  `REDIS_URL`.
- `redis` service in `docker-compose.yml`, with healthcheck and
  `depends_on` wiring on `web` and `worker`.
- `redis` database in `appliku.yml`.
- `worker.sh` script: `uv run python manage.py rqworker default`.
- `worker` service in compose, building from the same image as `web`,
  running `./worker.sh` instead of `./web.sh`.
- The django-rq dashboard mounted at `/django-rq/` (gated to staff by
  django-rq itself).

The first job a developer writes goes in `<their_app>/jobs.py`,
decorated with `@django_rq.job("default")`, and is enqueued via
`.delay(...)`. Tests can flip async off by overriding the queue's
`ASYNC` setting; Redis is still required at enqueue time for Job
persistence.

## Consequences

Positive:

- Adding a background job is a single-file change, not a refactor.
- The local-dev story matches production: one `docker compose up`
  starts the same web + worker + redis topology that runs in Appliku.
- Test suites that need inline execution have one knob to flip.

Negative:

- A Redis dependency on day one for projects that may never need it
  (the developer has to run `redis-server` locally or `docker compose
  up redis` before `runserver` works).
- A few extra lines in the Dockerfile/compose/appliku.yml that some
  generated projects will never use.

These costs are real but small; the alternative — discovering you need
async on week 6 and bolting it on across five files — has bitten this
codebase enough times to justify the upfront tax.

## Alternatives considered

- **Sync-only template, add async on demand.** Rejected — the retrofit
  cost across compose, Appliku, settings, and CI is the exact thing
  this decision is paying down upfront.
- **Celery instead of RQ.** Rejected — RQ + Redis is one fewer broker
  shape (Celery + Redis-or-RabbitMQ + result backend) and Python-native.
  The template optimises for "tiny mental model"; RQ wins.
- **Django 5's async views without a job runner.** Rejected — async
  views solve concurrency, not deferred work. A long-running outbound
  call still wants to live off the request thread.
