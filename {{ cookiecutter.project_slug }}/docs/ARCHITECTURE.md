# Architecture

Where the code lives and how its parts talk to each other. Domain terms are in
`GLOSSARY.md`, decisions in `docs/adr/`, production in `docs/OPERATIONS.md`.

## Code map

Django apps (boundaries in `tach.toml`): `core` (settings, URLs, API mount,
SPA), `users`, `api_keys`.

Each app uses this shape, with only the files it needs:

- `<app>/models.py`, `api.py` (ninja router), `schemas.py`, `services.py`,
  `admin.py`, `tests/`.
- An app's frontend lives in `core/frontend/src/spa/`, not in the app:
  `queries/` (TanStack Query hooks), `routes/` (one file per page) and
  `hooks/` (the only place for effects and timers; biome fails them anywhere
  else).

Shared places:

- `core/urls.py`: every HTML route. `core/frontend/src/spa/App.tsx`: the SPA
  routes.
- `core/api.py`: the ninja API and its default auth.
- `core/frontend/src/spa/api/schema.d.ts`: the generated API client types.
  `make schema` regenerates it (see Frontend & API contract).
- `core/frontend/src/spa/components/`: shared UI (`ui/` is shadcn).
- `core/tests/live/test_journey.py`: the one live journey (see
  `CODING_STANDARDS.md`).

## Module boundaries

`tach.toml` declares which apps may depend on which (`[[modules]]`) and which
of an app's modules other apps may import (`[[interfaces]]`). `tach check`
runs in `make lint` and pre-commit and fails on a runtime import the graph does
not permit. The baseline graph is two arrows out of `core`: `core → api_keys`
and `core → users`; `api_keys` and `users` may import nothing.

- **A `TYPE_CHECKING` import may cross a boundary** (ADR-0005), also for a
  `models` type the interface hides. Pair it with
  `from __future__ import annotations`:

  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:
      from other_app.models import Thing  # for type hints only


  def handle(thing: Thing) -> None: ...
  ```

  It has to point the way the runtime arrow points or would point. `api_keys`
  naming `users.models.User` is honest: a key belongs to a user, and `users`
  knows nothing about keys. `api_keys` naming a `core` type would hide an
  inverted `api_keys → core` dependency.
- **A new app adds one `[[interfaces]]` block.** Other apps may import only
  what it exposes. An app without a block exposes everything.

  ```toml
  [[interfaces]]
  expose = ["api(\\..*)?", "services(\\..*)?"]
  from = ["new_app"]
  ```

  `expose` entries are full-match regexes on the path below the app, so `api`
  alone exposes the name `api` but not `api.router`; append `(\\..*)?` to
  expose the module and its members.
- **For a "write through `services`" seam between apps, expose `services` and
  not `models`.** A direct `from app.models import …` from another app then
  fails `tach check`, while a guarded import for an annotation stays legal.
- **Sub-package `[[modules]]` are for layering inside one app.** An interface
  gates what other apps import, not what an app's own modules import. To keep
  `app.api` away from `app.models`, declare `app.models` and `app.services` as
  distinct `[[modules]]`: `app.models` depends on nothing, `app.services` may
  depend on `app.models`, and `app` and other apps depend on `app.services`
  only. Add the blocks only once the packages exist: a block on an absent path
  enforces nothing, and `tach check` only warns about it.
- **Tests, migrations, management commands and `manage.py` are excluded.** A
  management command is a composition root that may wire anything.

## Surfaces

HTML routes, all login-required except `/accounts/*`, `/admin/` and
`/healthz`. The SPA pages share one mount (`core.views.app_view`); their
behaviour lives in their route file. Every route in `App.tsx` needs its path in
`core/urls.py`, or a hard reload of that page answers 404
(`core/tests/test_frontend_wiring.py` checks it).

- `/accounts/login/`, `/accounts/logout/`: Django auth views. Password change
  and reset are not mounted, so those URLs 404. The login page loads the SPA
  bundle for its styles; `main.tsx` finds no `#app` there and does not mount.
  Its logo (`core/templates/_logo.html`) mirrors the SPA's
  `components/layout/logo.tsx`: update both together. `LogoutView` accepts
  only POST, so the SPA logs out with a form, not a link.
- `/accounts/google/login/` and its callback: allauth, mounted only when
  `GOOGLE_OAUTH_CLIENT_ID` is set (ADR-0009).
- `/admin/`: Django admin. `/admin/login/` redirects to `/accounts/login/`, so
  there is one login page.
- `/django-rq/`: queue dashboard, staff only. django-rq gates it itself, so
  `core/urls.py` adds no decorator.
- `/healthz`: anonymous probe, see `docs/OPERATIONS.md` "Health probing".

API: django-ninja under `/api/`, mounted in `core/api.py`, with an app's
router in `<app>/api.py`. The endpoint reference is the generated `/api/docs`
page (and `schema.d.ts`). `/api/docs` and `/api/openapi.json` need no login.

## Authentication

A user logs in with a username and password (an account created in the
admin), or with Google, gated by the SSO allowlist (`docs/OPERATIONS.md` "SSO
allowlist", ADR-0009).

Every `/api/` endpoint accepts **either** auth method, with one exception
(below):

- `ninja.security.django_auth`: session cookie set by `/accounts/login/`. Used
  by the SPA. CSRF enforced via `X-CSRFToken` header read from the CSRF cookie
  (`CSRF_COOKIE_NAME`, `csrftoken` by default). `csrfFetch`
  (`src/spa/api/csrf.ts`) sets the header. `openapi-fetch` calls it with a
  `Request` and an empty `init`, so it reads the method from either.
- `HttpBearer` against `UserApiKey`: `Authorization: Bearer
  {{ cookiecutter.project_slug }}_live_…`. Used by headless callers. No CSRF
  (state-changing requests are token-bound, not cookie-bound). A deactivated
  user's keys stop working at once: `verify()` rejects a key whose owner has
  `is_active=False`. `revoked_at` stays unset, so reactivating the user restores
  them.

Both auth paths resolve to the same `request.user`. The default list in
`core/api.py` tries the bearer first: `django_auth` runs its CSRF check before
it reads the session cookie, so in the other order it would answer a
bearer-authed write with 403 before `ApiKeyBearer` ran.

The `/api/api-keys/*` router is the single exception: it overrides the global
default to **`auth=django_auth` only**. See ADR-0002. A bearer token is
rejected there even when valid: `401` on list, and `403` on mint and revoke,
because `django_auth` runs its CSRF check before it looks at the session and a
bearer caller has no CSRF token. Each endpoint scopes by `request.user`;
revoking a key the requester does not own answers `404`, not `403`, so
existence is not disclosed. `POST /api/api-keys/` carries ninja's
`AuthRateThrottle` at ten mints per hour, keyed on the user.

### Google login

django-allauth with its Google provider (ADR-0009). What is mounted and what
is not:

- Only the two views of the redirect flow, and only when
  `GOOGLE_OAUTH_CLIENT_ID` is set. allauth's own login, signup, password reset
  and email pages are not mounted. Django's `LoginView` and `LogoutView` stay
  the login and logout views.
- Every outcome that is not a login redirects to the login page with a
  message. That includes an inactive user, whom allauth would answer with a
  page of its own.
- allauth never sends mail: the allowlist rejects unverified emails, so
  `SOCIALACCOUNT_EMAIL_VERIFICATION` is `none`.
- The account adapter drops allauth's own messages, because the SPA renders
  none and one would surface on the next login page.
- The one allauth template in reach is the confirmation page a direct GET on
  `/accounts/google/login/` renders; the login form POSTs past it.
- The provider is configured in settings, not as a `SocialApp` row, so there is
  no `django.contrib.sites` setup.

Users:

- A user created by Google login gets its full email as username. The email
  is unique, so `anna@company.com` and `anna@gmail.com` never clash.
- A Google login that links to an existing user keeps its password. allauth
  would make that password unusable, because nobody verified the address; that
  guards against an attacker who signed up with a victim's email and set the
  password. Here users only come from the admin, `createsuperuser` or Google
  login, so the adapter marks the linked email as verified first (allauth's
  `EmailAddress`), and such a user can use both logins.
- `User.email` is stored lowercased on every save. allauth links by exact
  match on the lowercased Google email, and Django's `normalize_email`
  lowercases only the domain, so a user saved as `Guest@gmail.com` would get a
  second user.
- The template ships no seed fixture and no default password on a server. Only
  the local `make up` creates an `admin` / `admin` superuser; `release.sh`
  never does.

### User

`users.User` is Django's `AbstractUser` with no extra fields, set as
`AUTH_USER_MODEL` from the first migration so a project can add fields later
without migrating away from `auth.User`. Foreign keys reference it through
`settings.AUTH_USER_MODEL`; code and factories import `users.models.User`.

### API keys

A user-issued bearer credential for the headless API path, stored as
`UserApiKey`. The raw token is `{{ cookiecutter.project_slug }}_live_` +
`secrets.token_urlsafe(32)`; only `sha256(token)` is persisted, and the raw
token is shown exactly once on creation. A user can hold several keys, named
per use case.

Provisioned two ways: self-service on the SPA's API Access page (list, mint
and revoke own keys), or the Django admin (emergency provisioning and
cross-user revoke). Both mint through `api_keys.services.mint`, which owns the
prefix and hash policy; the admin's `save_model` calls it instead of saving
the row itself. User-facing copy says **Revoke**: the row stays, so the
audit trail (`created_at`, `last_used_at`, `revoked_at`) is preserved, and
revoked keys stay listed with a "Revoked" badge.

## Request context

`core/request_context.py` puts a request id and a request source on every log
record and Sentry item of a request (`docs/OPERATIONS.md` "Correlating a
response with its logs and its Sentry items"). How the binding is held:

- `RequestContextMiddleware` is first in `MIDDLEWARE`, so a response another
  middleware produces is correlated too.
- The id is generated per request. An inbound `X-Request-ID` is never used: a
  client could collide unrelated requests onto one id.
- The binding outlives the middleware. `BaseHandler.get_response` logs a
  response of 400 and above after the middleware chain has returned, so the
  binding ends when the response closes (`request_finished`). Under WSGI a
  pooled thread serves the next request, so a binding left in place would leak
  into it. A request that finds a binding from a response that was never
  closed drops it first.
- The context variables are set, never reset through a token. A token is only
  valid in the context that created it, and a response can close in another.
- `response.close` is wrapped. `ASGIHandler` closes the response from a parent
  task, whose context may lack the binding, so there `close` runs in a copy of
  the request's context. WSGI closes in the request's own context, where
  running in a copy would leave the thread bound. An ASGI request never binds
  its caller's context.
- A flag of its own records that the middleware made the binding, so a response
  that closes inside a `bound()` block cannot undo that block's binding.
- The Sentry tags go on the isolation scope, which `DjangoIntegration` gives
  each request one of, so a tag cannot leak into the next request's events.
- `bound()` stores the pair on an exception that leaves the block. Such an
  exception is reported after the block has exited (by RQ's
  `handle_exception` for a job), and `tag_event_from_exception` reads the pair
  from it.
- `RequestContextFilter` is a logging filter, not a formatter change, because
  Sentry Logs indexes record attributes. It sits on the console handler because
  the SDK's logging hook runs after that handler and reads the same record.

## Background jobs

The template ships the runtime and no jobs (ADR-0003): `django-rq` with
`RQ_QUEUES` on `REDIS_URL`, a `worker` process built from the same image as
`web`, and the dashboard at `/django-rq/`.

- **A job goes in `<app>/jobs.py`**, decorated with
  `@django_rq.job("default")` and enqueued with `.delay(...)`. Wrap its body
  in `bound()` so its log lines and Sentry items carry an id
  (`docs/OPERATIONS.md` "Correlating a job").
- **In tests `.delay()` runs inline**: `core/settings/test.py` sets the
  queue's `ASYNC` to `False`. Redis is still required at enqueue time, for Job
  persistence.
- **The worker is the forking one**, `python manage.py rqworker default`. It
  runs in production and in the local stack, both in Linux containers, so
  macOS never forks. It raises `JobTimeoutException` inside a job that outruns
  `RQ_QUEUES` `DEFAULT_TIMEOUT` and kills one that is still running 60 seconds
  later.
- **Scheduling is off.** `worker.sh` runs without `--with-scheduler`, so a
  delayed job (`enqueue_in()`, `enqueue_at()`) is persisted but never moved
  onto the queue. Add `--with-scheduler` to `worker.sh` with the first delayed
  job; that one line is the whole migration. It is off until then because the
  scheduler polls Redis on an interval for the lifetime of every worker, and a
  fresh project has no delayed jobs for it to find.
- **What needs Redis.** RQ connects lazily, only when the worker runs or a job
  is enqueued, so most requests do not. `POST /api/api-keys/` does, because
  its throttle counters live in the Redis cache, and `/healthz` answers 503
  without it. `make test` does, because the observability suite runs a real
  worker against a real queue.

## Local stack

`make up` runs the topology of `compose.yaml` with the overlay
`compose.local.yaml`. Only `scripts/local-stack.sh` passes the overlay; a
deployment never sees it.

- The overlay makes `.env` optional, gives the stack its own image name,
  replaces the published port and sets the local app settings, including
  `HTTPS_ENFORCED=false` so login works over plain HTTP while `DEBUG` stays
  off.
- Every worktree gets its own stack. The compose project name is the project
  slug plus a short hash of the worktree's absolute path, and the image is
  named after the project name.
- The web port is the first free one from 8000, kept while the stack runs.
- Browsers share `localhost` cookies across ports, so the session and CSRF
  cookie names carry the compose project name as a suffix. The port can change
  after `make down`, the project name cannot, so a session survives a restart
  on another port.
- The script supplies the values compose interpolates, such as
  `POSTGRES_PASSWORD`. Values set in the compose files win over `.env`, so a
  copied `.env.example` cannot change the local topology.
- The overlay sets `SENTRY_ENVIRONMENT=local`, so a `SENTRY_DSN` from `.env`
  never reports as production.
- The local superuser is created by `make up`, never by `release.sh`.
- Only `web` builds the image; `release` and `worker` reuse it. After a
  rebuild, `make up` prunes the image it replaced, so a stack keeps one image.
- `make doctor` checks the Docker daemon, the Compose and Engine versions and
  the lockfiles. `make up` runs it first.

## Test harness

Reasons behind the test setup that no test name carries.

`core/settings/test.py`:

- `DJANGO_ALLOW_ASYNC_UNSAFE` is set because Playwright's sync API runs in an
  event loop, where Django's async-safety guard rejects the `live_server`
  fixture's database calls with `SynchronousOnlyOperation`.
- The `django-vite` manifest is read from `core/static/dist/js/`, not from
  `STATIC_ROOT`, so `make test` needs `make frontend.build` and no
  `collectstatic`.
- The cache is the dummy backend, so throttle counters do not leak between
  tests.
- `WHITENOISE_AUTOREFRESH` skips whitenoise's `STATIC_ROOT` scan, which warns
  "No directory at: staticfiles" because a test run never runs `collectstatic`.
- Passwords are hashed with MD5: PBKDF2 costs about 0.13 s per test that builds
  a user with `UserFactory`, against about 0.005 s of actual work. Re-profile
  before removing it.

Sentry (`conftest.py`, `core/tests/sentry_capture.py`,
`core/tests/test_observability.py`):

- An autouse fixture forks the Sentry scopes per test. The SDK's WSGI and ASGI
  handlers fork them per request, the test client does not, so a tag set by one
  test's request would reach the next test.
- The `sentry` fixture puts a client with a capturing transport on the global
  scope and restores the previous one. It does not call `sentry_sdk.init`,
  which would leave a client for the rest of the suite.
- `UNRESOLVABLE_TEST_DSN` parses, but its host never resolves. It is the
  backstop for anything that initializes the real SDK without a capturing
  transport.
- `boot_in_a_child_process` exists because the SDK initializes once per
  process, during `django.setup()`, which the suite has already passed.
- `perform_failing_jobs_on_a_real_worker` runs an RQ worker because RQ's
  integration reports from `Worker.handle_exception` alone, which the
  synchronous enqueue of the test settings never reaches. A failed job carries
  RQ's default one-year `failure_ttl`, so the helper deletes its keys.
- `console_output` swaps the stream of the stream handlers instead of reading
  captured stderr: a handler holds the `sys.stderr` it was built with, which
  pytest replaced later.
- `TestHealthzIsSilent` calls the WSGI handler, not the test client: the SDK's
  request handling lives in `WSGIHandler.__call__`, which the test client
  bypasses. It uses `django_db(transaction=True)` because the handler's
  `close_old_connections` closes a non-autocommit connection, which on Postgres
  breaks the default test transaction (503 from `/healthz`).

Request context (`core/tests/test_request_context.py`):

- `asgi_get_through_the_handler` speaks ASGI to `core.asgi.application`
  instead of using `AsyncClient`, which bypasses the parent-task close in
  `ASGIHandler.handle()`.
- `serve_wsgi` calls `core.wsgi.application`, not a new
  `get_wsgi_application()`: that re-runs `django.setup()`, whose logging
  `dictConfig` replaces the root handlers and takes caplog's with it.
- `wsgi_get_closed_in_a_foreign_context_like_asgi` reproduces the ASGI close
  from another context without Django's ASGI machinery in the way.
- The probe middleware is appended last, so it runs innermost, inside the
  request-id binding.

Other:

- `freshly_imported_production_settings` imports the real settings in a new
  interpreter, because they are read from the environment once, at import time.
- The Google login tests sign the ID token with an arbitrary key: allauth skips
  the signature check for an ID token it fetched from Google's token endpoint
  itself, over TLS.
- `core.urls` reads `SOCIALACCOUNT_PROVIDERS` at import. A test that blanks the
  setting resolves a URL first, or the process keeps a URLconf without the
  Google routes.
- The live journey suffixes the cookie names like a local stack does, and
  checks the boot data seam (server-rendered project name next to the
  username from `/api/me`): only a browser proves the SPA handles both.

## Frontend & API contract

The authenticated app is a React SPA (TypeScript, shadcn/ui on Tailwind v4,
`react-router` v8, TanStack Query). Django serves a single mount template at
every SPA route carrying `@login_required` + `@ensure_csrf_cookie`; the SPA
bundle is loaded via `django-vite`'s manifest. Server state lives in TanStack
Query.

SPA imports flow one way: `App.tsx -> routes -> components -> queries -> api`,
with `lib` and `components/ui` usable from anywhere. `biome.json` enforces it:
`components`, `queries`, `api` and `lib` import nothing to their left, and routes,
components and hooks reach the API client only through `queries`.

The SPA's typed API client is generated from ninja's OpenAPI schema using
`openapi-typescript` (types) + `openapi-fetch` (typed fetch). `make schema`
generates everything below the ninja `Schema` classes:

```
<app>/schemas.py  (Python ninja Schema classes, written by hand: the SOURCE)
  └─ manage.py export_openapi_schema → .openapi.json (transient, gitignored)
       └─ openapi-typescript → src/spa/api/schema.d.ts (GENERATED, never hand-edit)
            └─ import type { components } in the FE api layer
```

`make schema` runs that pipeline **offline**: `export_openapi_schema`
introspects the API in-process (no running server, no DB connection), so it also
works in CI. The committed `schema.d.ts` is raw `openapi-typescript` output
(`biome.json` excludes it from formatting so it stays byte-identical), and the
**`schema-fresh` pre-commit hook** (manual stage, like `pip-audit`) regenerates
it and fails if it drifts from `schemas.py`. Run `make schema` and commit.

`typescript` stays on `^5.9`: `openapi-typescript` declares a peer range on
TypeScript 5.x, so raise the pin only once it supports the next major.

Schema conventions are in `CODING_STANDARDS.md`.

The SPA boot payload is split by nature (`CODING_STANDARDS.md` "Boot data"):
build-time **constants** are server-rendered. The `core.context.site` context
processor injects `project_name` and `csrf_cookie_name`, the mount template
emits them as `data-project-name` and `data-csrf-cookie-name` on `#app`, and
`main.tsx` reads them from `mountNode.dataset`. Per-user **data** (`username`)
is fetched from the typed `GET /api/me` (schema `core.schemas.MeOut`) via
`useMe()`. `/api/me` accepts both auth methods, so it doubles as a headless
`whoami`. The "Signed in as …" footer resolves after that fetch, not on first
paint.

Build is a single Vite pipeline using `@tailwindcss/vite`.
