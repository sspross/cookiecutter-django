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
default to **`auth=django_auth` only**. See ADR-0002.

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
  checks the ADR-0006 boot seam (server-rendered project name next to the
  username from `/api/me`): only a browser proves the SPA handles both.

## Frontend & API contract

The authenticated app is a React SPA (TypeScript, shadcn/ui on Tailwind v4,
`react-router` v8, TanStack Query). Django serves a single mount template at
every SPA route carrying `@login_required` + `@ensure_csrf_cookie`; the SPA
bundle is loaded via `django-vite`'s manifest. Server state lives in TanStack
Query.

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

The SPA boot payload is split by nature (ADR-0006): build-time **constants** are
server-rendered (`project_name` → `data-project-name` on `#app`, read via
`mountNode.dataset`), while per-user **data** (`username`) is fetched from the
typed `/api/me` via `useMe()`.

Build is a single Vite pipeline using `@tailwindcss/vite`.
