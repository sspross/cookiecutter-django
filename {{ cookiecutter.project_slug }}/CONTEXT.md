# Context

## Glossary

### API Key
A user-issued bearer credential for the headless API path. Stored as `UserApiKey`
(`user FK, name, prefix, hash, created_at, last_used_at, revoked_at`). The raw token is
`{{ cookiecutter.project_slug }}_live_` + `secrets.token_urlsafe(32)`; only `sha256(token)`
is persisted. Provisioned two ways: (1) self-service in the SPA's **API Access** section —
list / mint / revoke own keys; (2) Django admin (kept for emergency provisioning and
cross-user revoke). The raw token is shown exactly once on creation. A user can hold
multiple keys (rotatable, named per use case). "Delete" in user-facing copy means
**revoke** — the row stays so the audit trail (`created_at`, `last_used_at`,
`revoked_at`) is preserved; revoked keys remain listed but visually marked.

### Soft-delete vocabulary
Two distinct soft-delete semantics live in this codebase, and the naming makes the
distinction load-bearing:

- **`revoked_at` / `is_revoked`** — *visible-but-marked*. The row stays listed in the
  user-facing surface and is rendered with a "(revoked)" indicator. Used by `UserApiKey`
  so the audit trail (`created_at`, `last_used_at`, `revoked_at`) stays in front of the
  owner.
- **`deleted_at` / `is_deleted`** — *hidden from users*. The row is filtered out of
  every user-facing read and only operators see it (Django admin, raw DB).

No model in the template uses `deleted_at` yet — adopt that pattern when you need
"hide from users" semantics. When introducing soft-delete on a new model, pick the
pattern that matches the desired visibility — never invent a third name. Both
patterns share the same field shape: a nullable `DateTimeField` plus an `is_*`
`@property`.

## Surfaces

Routes (all login-required except `/accounts/login/` and `/admin/`):

HTML pages:

- `/` — Django shell that mounts the React SPA on the **Dashboard** route.
- `/api-access/` — same SPA mount, react-router renders the **API Access** route.
- `/accounts/login/` & `/accounts/logout/` — Django built-in auth views.
  Load the SPA bundle so visual tokens match; `main.tsx` finds no `#app`
  node there and bails before mounting React.
- `/admin/` — Django admin; superuser creates non-staff `User` accounts here,
  mints `UserApiKey` rows through the standard add form, and revokes them via a
  custom admin action.
- `/django-rq/` — django-rq queue dashboard, gated to staff users by django-rq itself.

API (django-ninja, dual auth, CSRF on session-authed writes):

- `GET  /api/me` — the current user (`{username}`, schema `core.schemas.MeOut`).
  Dual auth, so it doubles as a headless `whoami`; the SPA reads it via
  `useMe()` for the "Signed in as …" footer. See ADR-0006.
- `GET  /api/api-keys/` — list the requesting user's keys (active and revoked,
  newest-first)
- `POST /api/api-keys/` — body `{name}`; responds 201 with the created row plus the
  raw token, the only place the server ever returns it
- `POST /api/api-keys/{id}/revoke/` — idempotent soft-delete; cross-user 404, not 403

Every endpoint accepts **either** auth method by default:

- `ninja.security.django_auth` — session cookie set by `/accounts/login/`. Used by
  the SPA. CSRF enforced via `X-CSRFToken` header read from the `csrftoken` cookie.
- `HttpBearer` against `UserApiKey` — `Authorization: Bearer
  {{ cookiecutter.project_slug }}_live_…`. Used by headless callers. No CSRF
  (state-changing requests are token-bound, not cookie-bound).

Both auth paths resolve to the same `request.user`.

The `/api/api-keys/*` router is the single exception: it overrides the global
default to **`auth=django_auth` only**. A leaked bearer token cannot be used to
mint or revoke keys, so revocation by the user remains a clean kill. See ADR-0002.

App layout:

```
core/                # settings package and Django app in one (namespace package)
  admin.py           # empty — scaffold for your own admin registrations
  models.py          # empty — scaffold for your own models
  api.py             # NinjaAPI mount; [ApiKeyBearer(), django_auth]; GET /api/me
  context.py         # template context_processor: project_name
  schemas.py         # MeOut — the /api/me wire shape
  settings/
    base.py          # env-driven settings
    test.py          # test overrides (async guard, MD5 hasher, vite manifest)
  management/commands/
    export_openapi_schema.py  # offline OpenAPI JSON dump (make schema / guard)
  migrations/
  urls.py
  views.py           # app_view: SPA mount; @login_required + @ensure_csrf_cookie
  asgi.py
  wsgi.py
  templates/
    _base.html       # vite-aware base; Geist, Geist Mono and Inter webfonts
    _logo.html       # mirror of spa/components/layout/logo.tsx
    core/app.html    # SPA mount template
    registration/login.html
  tests/
    test_views.py
    test_api.py      # /api/me (session + bearer + anonymous)
api_keys/
  __init__.py
  apps.py
  admin.py           # UserApiKeyAdmin (standard add flow + revoke action)
  api.py             # ninja Router, /api/api-keys/* (django_auth only)
  auth.py            # HttpBearer subclass resolving Bearer token → User
  models.py          # UserApiKey
  schemas.py         # ApiKeyOut, ApiKeyCreateIn, ApiKeyMintOut
  services.py        # mint(), verify(), revoke() — token engine
  tests/
    factories.py
    test_models.py
    test_services.py
    test_api.py
    live/
      test_mint_flow.py
```

SPA source layout under `core/frontend/src/`:

```
main.tsx            # React entry (Vite build input); QueryClientProvider + Router
spa/
  App.tsx           # routes: / (Dashboard), /api-access (ApiAccess)
  index.css         # @import "tailwindcss"; shadcn CSS variables
  api/
    schema.d.ts     # generated by openapi-typescript; freshness-guarded, never hand-edit
    client.ts       # openapi-fetch instance + csrfFetch wrapper
    csrf.ts
  queries/
    use-api-keys.ts # TanStack Query hooks for api keys
    use-me.ts       # useMe() — current user from /api/me
  routes/
    index.tsx       # Dashboard (inline cards, no abstractions yet)
    api-access.tsx
  components/
    api-key-modals.tsx
    copy-button.tsx # clipboard button (curl block + reveal modal)
    layout/
      app-shell.tsx # sidebar + main content
      logo.tsx
      icons.tsx
      theme-toggle.tsx
    ui/             # shadcn primitives: card, dialog, button, input,
                    # label, badge, table, skeleton (8 only — `npx shadcn add`
                    # the rest as needed)
  lib/
    utils.ts        # cn() helper
```

### Frontend & API contract
The authenticated app is a React SPA (TypeScript, shadcn/ui on Tailwind v4,
`react-router` v7, TanStack Query). Django serves a single mount template at `/` and
`/api-access/` carrying `@login_required` + `@ensure_csrf_cookie`; the SPA bundle is
loaded via `django-vite`'s manifest. Login (`/accounts/login/`) stays Django-rendered,
Tailwind-styled to match.

The SPA's typed API client is generated from ninja's OpenAPI schema using
`openapi-typescript` (types) + `openapi-fetch` (typed fetch). The hand-written
ninja `Schema`s in `*/schemas.py` are the **single source of truth**; everything
to their right is generated:

```
<app>/schemas.py  (hand-written ninja Schema — the SOURCE)
  └─ manage.py export_openapi_schema → .openapi.json (transient, gitignored)
       └─ openapi-typescript → src/spa/api/schema.d.ts (GENERATED, never hand-edit)
            └─ import type { components } in the FE api layer
```

`make schema` runs that pipeline **offline** — `export_openapi_schema`
introspects the API in-process (no running server, no DB connection), so it also
works in CI. The committed `schema.d.ts` is raw `openapi-typescript` output
(`biome.json` excludes it from formatting so it stays byte-identical), and the
**`schema-fresh` pre-commit hook** (manual stage, like `pip-audit`) regenerates
it and fails if it drifts from `schemas.py` — run `make schema` and commit. This
is the guard that stops the generated client silently rotting out of date.

Schema conventions (so the generated TS and API docs stay rich):

- **Enum-ish fields use `Literal[...]`, not `str`** — keep the literals in sync
  with the model's `TextChoices`. `str` collapses to a bare TS `string`;
  `Literal` gives the FE a real union.
- **Document fields with `Field(description=...)`, not `#` comments** — only the
  `Field` description reaches OpenAPI, so it flows into both the generated TS
  (`@description` JSDoc on hover) and the `/api/docs` page. A docstring on the
  `Schema`/endpoint propagates the same way (see `schema.d.ts`).
- **Optional artifact:** a Pydantic field with a default (`x: T | None = None`)
  renders as `x?:` *optional* in the generated TS even though the server always
  serializes it. Either coalesce at the use site or accept the widened type;
  don't drop the default to "fix" the type (it changes the API contract).

Server state lives in TanStack Query. Cache is keyed by query key, so list views
and detail views can share the same cached row.

The SPA boot payload is split by nature (ADR-0006): build-time **constants** are
server-rendered (`project_name` → `data-project-name` on `#app`, read via
`mountNode.dataset`), while per-user **data** (`username`) is fetched from the
typed `/api/me` via `useMe()`. No untyped `window` global.

Build is a single Vite pipeline using `@tailwindcss/vite`. The same compiled CSS file
is loaded by both the SPA mount template and Django-rendered pages (login, admin
error pages), so visual tokens are shared.

### Testing

No JS unit tests. Frontend correctness is exercised end-to-end by the Python
**live tests** under `*/tests/live/`. A live test is a plain pytest function
taking pytest-django's `live_server` and pytest-playwright's `page` fixtures —
no bespoke base class. It drives the real SPA against a real Django server, so
it covers the same ground a vitest suite would — minus the mocking gymnastics.

Conventions:

- **Web-first assertions.** Use Playwright's auto-retrying `expect(locator)`
  (e.g. `to_be_visible()`, `to_contain_text()`, `to_have_count()`) rather than
  bare instant reads — the retry absorbs animation/transition timing.
- **Artifacts on failure** are captured natively by pytest-playwright into
  `test-results/` (a trace + screenshot; configured via the `--tracing` /
  `--screenshot` addopts in `pyproject.toml`). Inspect a trace with
  `uv run playwright show-trace test-results/<…>/trace.zip`.
- **Dev knobs** are Playwright-native: `uv run pytest --headed --slowmo 500`
  (wrapped by `make test.live.watch`), or `PWDEBUG=1` for the inspector.
- `core/settings/test.py` sets `DJANGO_ALLOW_ASYNC_UNSAFE` so the sync
  Playwright API can touch the DB from its event loop.
- **One journey, not many small e2e tests.** A live test drives a browser,
  which costs ~100x what a `client` test costs (the whole non-live suite runs
  in ~0.2s; the one live test takes ~2.3s). Extend the existing journey with
  another step rather than adding a second browser session, and only assert
  what a browser is needed for: real rendering, focus, keyboard, viewport,
  static serving. Anything reachable from `client` belongs in `tests/test_*.py`.
- `core/settings/test.py` also pins `PASSWORD_HASHERS` to MD5. The default
  PBKDF2 hasher is deliberately slow and dominated the suite; don't remove it
  without re-profiling.
- Coverage is configured in `pyproject.toml` and reported by
  `make test.coverage`. Use its diff to judge a deletion: a test whose removal
  changes no missed line was asserting something another test already covers.

Static correctness on the TS side is covered by `tsc --noEmit` and biome (both
run in pre-commit).

If you ever need a unit test that can't be expressed as a live test, add vitest
back — but justify it in a PR, don't reflexively install it for "we should have
unit tests."
