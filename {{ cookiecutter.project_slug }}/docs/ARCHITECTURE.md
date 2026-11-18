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
behaviour lives in their route file.

- `/accounts/login/`, `/accounts/logout/`: Django auth views. Password change
  and reset are not mounted, so those URLs 404. The login page loads the SPA
  bundle for its styles; `main.tsx` finds no `#app` there and does not mount.
- `/accounts/google/login/` and its callback: allauth, mounted only when
  `GOOGLE_OAUTH_CLIENT_ID` is set (ADR-0009).
- `/admin/`: Django admin. `/admin/login/` redirects to `/accounts/login/`, so
  there is one login page.
- `/django-rq/`: queue dashboard, staff only.
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
  (`CSRF_COOKIE_NAME`, `csrftoken` by default).
- `HttpBearer` against `UserApiKey`: `Authorization: Bearer
  {{ cookiecutter.project_slug }}_live_…`. Used by headless callers. No CSRF
  (state-changing requests are token-bound, not cookie-bound). A deactivated
  user's keys stop working at once: `verify()` rejects a key whose owner has
  `is_active=False`. `revoked_at` stays unset, so reactivating the user restores
  them.

Both auth paths resolve to the same `request.user`.

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
cross-user revoke). User-facing copy says **Revoke**: the row stays, so the
audit trail (`created_at`, `last_used_at`, `revoked_at`) is preserved, and
revoked keys stay listed with a "Revoked" badge.

## Frontend & API contract

The authenticated app is a React SPA (TypeScript, shadcn/ui on Tailwind v4,
`react-router` v8, TanStack Query). Django serves a single mount template at
every SPA route carrying `@login_required` + `@ensure_csrf_cookie`; the SPA
bundle is loaded via `django-vite`'s manifest. Server state lives in TanStack
Query.

SPA imports flow one way: `App.tsx -> routes -> components -> queries -> api`,
with `lib` and `components/ui` usable from anywhere. `biome.json` enforces who
may import routes and the API client.

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
