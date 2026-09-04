# Operations

The runbook for running `{{ cookiecutter.project_slug }}` in production.

Facts here are taken from the repo (`appliku.yml`, `compose.yaml`, `Dockerfile`,
`.github/workflows/image.yml`, `core/settings/base.py`, `core/views.py`,
`release.sh`, `web.sh`, `worker.sh`).
Anything that depends on the Appliku account or the hosting plan rather than on
this repo is marked **unverified**: confirm it in the Appliku dashboard and
correct this file.

Two deployment targets consume the same image and process scripts (ADR-0004):
Appliku via `appliku.yml`, and any docker-compose compatible host via
`compose.yaml`. Where the two differ, this runbook says which one it means.

## Architecture snapshot

One Docker image (`Dockerfile`) is built per deploy and runs three processes,
declared in both deployment manifests:

| Process | Command | What it does |
| --- | --- | --- |
| `web` | `./web.sh` | `gunicorn core.wsgi` on `0.0.0.0:${PORT:-8000}`, 5 workers, 120s timeout, logs to stdout |
| `worker` | `./worker.sh` | `manage.py rqworker default`, the forking RQ worker |
| `release` | `./release.sh` | `manage.py migrate`, run once per deploy before web and worker start |

The image's `CMD` is `./web.sh`, which only matters on a host that cannot
override the command; Appliku and compose both set the command per process.

Backing services, provisioned by the deployment target (Appliku from
`appliku.yml`, or the `db` and `redis` services in `compose.yaml`):

- `db`, Postgres 17. Reaches the app as `DATABASE_URL`.
- `redis`, Redis 7. Reaches the app as `REDIS_URL`. It carries two workloads at
  once: the RQ job queue and the Django cache.

Storage:

- Static files are collected into the image at build time
  (`manage.py collectstatic`) and served by WhiteNoise from the web process.
  There is no CDN or object store in the default setup.
- Uploaded media is written to the `media` volume, mounted at `/volumes/media`
  on both targets, and served at `/media/`. Django itself does not serve it in
  production: `core/urls.py` uses `django.conf.urls.static.static()`, which
  returns no patterns when `DEBUG` is false. On Appliku the platform proxy is
  supposed to serve the volume (`url: /media/` in `appliku.yml`);
  **unverified**. On compose nothing serves it out of the box: the reverse
  proxy in front of the stack has to. Confirm before shipping a feature that
  relies on user uploads being readable.

The container port is 8000 and the web process is exposed. Appliku terminates
TLS in front of it; a compose deployment publishes it on `127.0.0.1:8000` and
expects the reverse proxy to. Either way the proxy forwards
`X-Forwarded-Proto`, which `SECURE_PROXY_SSL_HEADER` trusts. With `DEBUG=false`
the app sets `SECURE_SSL_REDIRECT`, secure session and CSRF cookies, and one
year of HSTS.

## Environment variables

Names and defaults below come from `core/settings/base.py`; the production
source comes from `appliku.yml` on Appliku and from `compose.yaml` plus the
host's `.env` on a compose deployment.

| Variable | Required | Default (no value set) | Appliku source | Compose source |
| --- | --- | --- | --- | --- |
| `SECRET_KEY` | yes | none, the app fails to boot | set manually in Appliku (`source: manual`) | `.env` on the host |
| `DEBUG` | no | `False` | `appliku.yml` pins it to `"false"` | `compose.yaml` pins it to `"false"` |
| `DATABASE_URL` | yes | none, the app fails to boot | `db` database, private connection URL | `compose.yaml`, pointing at the `db` service with `${POSTGRES_PASSWORD}` |
| `REDIS_URL` | no | `redis://localhost:6379/0` | `redis` database, private connection URL | `compose.yaml`, pointing at the `redis` service |
| `ALLOWED_HOSTS` | no | `[]` (empty list) | `from_domains: true`, filled from the domains added in Appliku | `.env` on the host, needs `localhost` for the `web` healthcheck |
| `CSRF_TRUSTED_ORIGINS` | no | `[]` (empty list) | not set by `appliku.yml`, set it manually | `.env` on the host |
| `MEDIA_ROOT` | no | `<repo>/media` | injected from the `media` volume's `MEDIA` prefix | `compose.yaml`, `/volumes/media` |
| `MEDIA_URL` | no | `media/` | injected from the `media` volume's `MEDIA` prefix | `compose.yaml`, `/media/` |
| `PORT` | no | `8000` | **unverified** whether Appliku injects it; `container_port` is 8000 either way | unset, `web.sh` falls back to 8000 |
| `DJANGO_VITE_DEV_MODE` | no | unset, follows `DEBUG` | not set in production | not set in production |

`PORT` is not a Django setting: `web.sh` reads it to bind gunicorn
(`0.0.0.0:${PORT:-8000}`). Changing it means changing `container_port` in
`appliku.yml` or the port mapping in `compose.yaml` too.

`POSTGRES_PASSWORD` is compose-only. It never reaches Django; `compose.yaml`
interpolates it into the `db` service and into `DATABASE_URL`, without escaping,
so it has to be URL-safe.

Notes:

- `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` are comma-separated lists.
  `CSRF_TRUSTED_ORIGINS` entries need the scheme (`https://app.example.com`),
  `ALLOWED_HOSTS` entries do not (`app.example.com`).
- Set `CSRF_TRUSTED_ORIGINS` yourself for every domain that posts forms or calls
  the API with a session cookie. Nothing populates it automatically, and a
  missing entry shows up as a 403 on POST, not as a boot failure.
- Generate a `SECRET_KEY` with
  `python -c "import secrets; print(secrets.token_urlsafe(50))"`.

### Project-specific variables

_Placeholder: list the API keys, webhook secrets, and third-party credentials this project adds, and where each one is provisioned._

## Deploy flow

### Releases and the published image

A release is a semver git tag on `main`:

```
git tag v1.2.3 && git push origin v1.2.3
```

`.github/workflows/image.yml` builds `Dockerfile` on that tag and pushes
`ghcr.io/<owner>/<repo>:1.2.3` and `ghcr.io/<owner>/<repo>:latest` to GitHub
Container Registry, authenticated with the workflow's own `GITHUB_TOKEN`. On a
pull request the same workflow builds the image and does not push it, so a
`Dockerfile` that no longer builds, or an uncommitted lockfile change, fails CI
instead of a release.

Who consumes the tag depends on the target:

- Appliku ignores tags entirely and builds from `main` on push.
- A compose host that deploys this repo from git also ignores them and builds
  locally (`docker compose up -d --build`).
- A separate infra repo, where one exists, pins the tag in its production
  compose file. Bumping that pin is the deploy. See ADR-0004.

**Unverified**: whether the GHCR package is private by default for this
project's account, and which pull credentials a compose host therefore needs.

On Appliku:

1. Push to `main`.
2. Appliku builds the image from `Dockerfile`. The build installs dependencies,
   builds the Vite frontend, and runs `collectstatic`.
3. Appliku runs the `release` process: `release.sh`, which is only
   `uv run ./manage.py migrate`.
4. The `web` and `worker` processes run the new image.

**Unverified**: what a failed build or a failed release process does to the
version already running.

On a compose host: pull the new commit and run `docker compose up -d --build`.
The build is the same one. `release` runs to completion first; `web` and
`worker` are recreated only after it exited 0
(`condition: service_completed_successfully`), so a failing migration leaves the
previous containers running.

Per ADR-0004, migrations and one-shot tasks belong in `release.sh` rather than
in `web.sh`. `release.sh` currently holds nothing but `migrate`: it runs on
every deploy, so anything added there has to stay safe to re-run. A one-time
backfill belongs in a one-off command instead.

Rolling back means deploying an earlier commit. Migrations do not roll back with
it: a deploy that migrated the schema stays migrated, so a rollback is only safe
while the older code still runs against the new schema. Write migrations to stay
backwards compatible for one release (add columns nullable, drop them a release
later).

### Manual deploys and one-off commands

Deploys and one-off commands are triggered from the Appliku dashboard or its
CLI; see [docs.appliku.com/docs/cli-sdk](https://docs.appliku.com/docs/cli-sdk/).
Run management commands as `uv run ./manage.py <command>`, the same entry point
the process scripts use. **Unverified**: which environment a one-off command
receives, whether it gets its own container or attaches to a running one, and
how long it may run.

On a compose host the equivalent is
`docker compose run --rm web uv run ./manage.py <command>`, which starts a
throwaway container from the same image with the same environment.

## First superuser

After the first successful deploy, create the first superuser with a one-off
command in Appliku. One-off commands have no terminal attached, so the
interactive prompts fail; pass the credentials through the environment
variables Django reads with `--noinput`:

```
DJANGO_SUPERUSER_PASSWORD='<password>' uv run ./manage.py createsuperuser --noinput --username admin --email you@example.com
```

If the runner rejects the inline prefix, set `DJANGO_SUPERUSER_PASSWORD` as an
app environment variable, run the command without it, and remove the variable
afterwards.

On a compose host, interactive or with the same `--noinput` form:

```
docker compose run --rm web uv run ./manage.py createsuperuser
```

Then log in at `https://<your-domain>/admin/` and create further accounts there.
Nothing in the deploy path loads a fixture, so this is the only way an account
exists in production.

## Health probing

`/healthz` (no trailing slash) is an anonymous JSON probe. It accepts `GET` and
`HEAD` only and answers anything else with `405`. It never sets a cookie, and it
is listed in `SECURE_REDIRECT_EXEMPT` so it is not redirected to https. Probe it
over https anyway; the exemption is there for a checker that cannot.

Response body, always both keys:

```json
{"database": "ok", "redis": "ok"}
```

Each value is `ok` or `error`. The status is `200` when both are `ok` and `503`
when either is `error`. The checks are a `SELECT 1` against the default database
and a `PING` against the RQ Redis connection.

```
curl -i https://<your-domain>/healthz
```

Read a `503` as "the app is up but a dependency is not": the process is serving,
so the body says which side to look at.

`compose.yaml` probes it as the `web` service's healthcheck (every 30s, three
retries), which is what marks the container healthy or unhealthy.

**Unverified**: whether Appliku probes this endpoint itself, and whether a
failing probe pulls the instance out of rotation. Point whatever uptime checker
this project uses at this URL.

### Monitoring targets

_Placeholder: name the uptime checker, the alert channel, and who is on call._

## Logs and monitoring

Everything logs to stdout and stderr, so the platform's log stream is the only
log sink. There is no log file and nothing is written to disk.

- gunicorn runs with `--log-file -`, which is its **error** log only. `web.sh`
  passes no `--access-logfile`, so there is no per-request access log. Add
  `--access-logfile -` to `web.sh` if you need one; expect the volume.
- Django logging is configured in `core/settings/base.py`: a single console
  handler, format `{levelname} {name} {message}`. Root is `WARNING`. The
  project's own apps (`core`, `api_keys`, `users`) and `django` log at `INFO`.
  `django.request` is at `ERROR`, which keeps bot 404 probes (logged at
  `WARNING`) out of the stream.
- Raising verbosity for one app means editing `LOGGING` and deploying. There is
  no env-var log-level knob.
- Queue state is visible in the app itself at `/django-rq/`, django-rq's own
  dashboard, gated to staff users by django-rq.

**Unverified**: Appliku's log retention window, and whether log drains to an
external service are available on the current plan.

### Error tracking

_Placeholder: no error tracker is wired in the template. Record which one this project uses and where its DSN is set._

## Database backups and restore

On Appliku the Postgres instance is the managed `postgresql_17`.

**Unverified**: whether Appliku takes automatic backups, how often, how long they
are kept, and whether point-in-time recovery is available. Confirm this in the
dashboard before relying on it, and write the answer here.

On a compose host it is the `db` service, storing its data in the
`postgres-data` named volume. Nothing backs that up: the template ships no
backup job, so a compose deployment needs one on the host (a `pg_dump` from
`docker compose exec db` on a schedule, shipped off the machine).

Taking a manual dump: the deployed image installs `libpq-dev` but **not**
`postgresql-client`, so `pg_dump` and `pg_restore` are not available in a one-off
command. Two options:

- Connect from outside with a `DATABASE_URL` and run `pg_dump` locally. This
  needs an externally reachable connection URL; `appliku.yml` wires the *private*
  one into the app. **Unverified**: how to obtain the public connection URL.
- Add `postgresql-client` to the `apt-get install` list in `Dockerfile` if
  dumping from inside a one-off command is the workflow you want.

Run a restore drill at least once before you need it: restore a dump into a
scratch database, point a local checkout at it, and run the app against it. An
untested backup is not a verified backup.

### Restore procedure

_Placeholder: write the exact commands once the backup mechanism above is confirmed, including who is allowed to run them._

## Redis durability

Redis carries two workloads on one instance:

- The RQ queue (`RQ_QUEUES["default"]`), which is where job payloads live.
  Enqueued and in-flight job state exists nowhere else.
- The Django cache (`CACHES["default"]`, `RedisCache`) under the key prefix
  `{{ cookiecutter.project_slug }}`.

Consequences to hold on to:

- **Never call `cache.clear()` in production.** Django's `RedisCache.clear()`
  issues `FLUSHDB`, which wipes the whole database, queued jobs included. Delete
  specific keys instead.
- Losing Redis loses queued jobs. Write jobs so a lost job is recoverable: keep
  the source of truth in Postgres and make the job re-enqueueable, rather than
  treating the queue as durable storage.
- The cache is not a store either. Anything that must survive a restart belongs
  in Postgres.

**Unverified**: the persistence configuration of Appliku's managed `redis_7`
(RDB snapshots, AOF, or neither) and whether its contents survive a restart.
Until that is confirmed, assume the queue is volatile. On a compose host the
`redis` service runs the stock `redis:7` image with a `redis-data` volume on
`/data`, so it keeps the image's default RDB snapshots and nothing more. Assume
the queue is volatile there too.

## Troubleshooting

| Symptom | Likely cause | Where to look |
| --- | --- | --- |
| Boot fails with `ImproperlyConfigured: Set the SECRET_KEY environment variable` | `SECRET_KEY` not set | environment variables in the Appliku dashboard, or `.env` on the compose host |
| Boot fails on `DATABASE_URL` | the `db` database is not attached | the `from_database` block in `appliku.yml`, or the `db` service and `POSTGRES_PASSWORD` on a compose host |
| `400 Bad Request` / `DisallowedHost` on every request | the domain is missing from `ALLOWED_HOSTS` | whether the domain is added in Appliku, so `from_domains` picks it up; on compose, `ALLOWED_HOSTS` in `.env` (`localhost` included) |
| `403 CSRF verification failed` on POST while GET works | the origin is missing from `CSRF_TRUSTED_ORIGINS` | set it manually, including the `https://` scheme |
| `/healthz` returns 503 with `"redis": "error"` | Redis is down or `REDIS_URL` is wrong | Redis instance status, then the env var |
| `/healthz` returns 503 with `"database": "error"` | Postgres is down or unreachable | database status, connection limit |
| The app serves but jobs never run | the `worker` process is stopped or crash-looping | worker logs, then `/django-rq/` for queue depth |
| A deploy succeeds but the schema is old | `release.sh` failed | release process logs, or `docker compose logs release` |
| `ValueError: Missing staticfiles manifest entry` | a template references a static file that was not collected | the `collectstatic` step in the build log |
| Redirect loop on https | `SECURE_PROXY_SSL_HEADER` is not receiving `X-Forwarded-Proto` | proxy configuration; expected to work as-is on Appliku, has to be configured on the reverse proxy in front of a compose stack |

### Known project-specific failure modes

_Placeholder: add the incidents this project has actually seen, with the symptom and the fix._
