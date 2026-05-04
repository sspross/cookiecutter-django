# {{ cookiecutter.project_name }}

A Django + typed React/TypeScript SPA project, generated from
[cookiecutter-django](https://github.com/sspross/cookiecutter-django).

> **The example resources ship without authentication.** This template's demo
> runs anonymously by design. Do not deploy a project derived from it
> publicly without first wiring up Django auth and per-resource permissions.

## Architecture

- **Backend**: Django + [Django Ninja](https://django-ninja.dev/). One
  shared `NinjaAPI` instance lives in `core` (`core/api.py`); every app
  contributes endpoints by exporting a `Router` mounted there. The whole
  project produces a single OpenAPI document.
- **Frontend**: React 19 + TypeScript (strict, including
  `noUncheckedIndexedAccess`) + Vite, at `frontend/`. TanStack Router
  (code-based) drives client-side navigation, TanStack Query is the data
  layer, and `openapi-fetch` is the runtime client typed against
  `frontend/types/api.d.ts`.
- **Type contract**: `make codegen` regenerates `frontend/types/api.d.ts`
  from the live OpenAPI document. `make codegen.check` fails if the
  committed types are stale relative to the schema.
- **Static**: `STATICFILES_DIRS` includes `frontend/dist`, so a single
  `collectstatic` aggregates the Vite bundle and Django admin assets into
  one `STATIC_ROOT`. The same artifact is served by both deploy paths.
- **SPA shell**: A catch-all view in `core` returns `index.html` for any
  non-API/non-admin/non-static path — this is what serves the SPA in the
  WhiteNoise/Appliku deploy. The Caddy/compose deploy serves `index.html`
  directly from disk and never hits Django for those paths.

## Setup

- Copy `.env.example` to `.env` and adjust `DATABASE_URL` if needed
  (defaults to SQLite)
- `uv sync`
- `uv run pre-commit install`
- `uv run playwright install chromium`
- `make db.recreate`
- `make db.initialize`
- `make frontend.install`
- `make frontend.build`
- `uv run python manage.py collectstatic --noinput`

## Local development

Three predictable commands in three terminals:

```bash
make dev.up       # Postgres + Caddy in docker compose
make dev.django   # Django on the host
make dev.vite     # Vite dev server on the host
```

Caddy listens on `http://localhost:8080` and proxies:

- `/api/*`, `/admin/*`, `/media/*` → Django on `host.docker.internal:8000`
- everything else → Vite on `host.docker.internal:5173`

This keeps file-watching and native debugger attach fast while still giving
the SPA a same-origin view of the API (so cookies, CSRF, and SameSite
behave like prod). To tear everything down: `make dev.down`.

### Generated types

The SPA's `openapi-fetch` client is typed against
`frontend/types/api.d.ts`, which is generated from the live OpenAPI
document. The `.d.ts` is **committed**; the intermediate `openapi.json`
is regenerated on demand and is not.

Run `make codegen` after any change that affects the OpenAPI surface — a
new or edited Ninja schema, router, response shape, query param, or
status code:

```bash
make codegen
```

Commit the regenerated `frontend/types/api.d.ts` along with the backend
change. CI runs `make codegen.check`, which regenerates the types and
fails if `git diff` against the committed `.d.ts` is non-empty. A
failure means the backend changed but the committed types weren't
regenerated — re-run `make codegen` locally and commit the diff.

## Stage Deployment

### Docker compose with Caddy

The compose stack is three services: `app` (Django via gunicorn), `caddy`
(serves baked static + reverse-proxies the app), and `postgres`. The
project Caddy listens on plain HTTP on an internal port; an outer Caddy
(or Cloudflare) handles TLS at the edge.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The SPA bundle is **baked into the Caddy image** at build time. Deploys
are atomic — rolling back is a single image-tag change. Cache headers
match Cloudflare's expectations: hashed Vite assets get
`Cache-Control: public, max-age=31536000, immutable`, the SPA `index.html`
is `no-cache`, and media uses a short `max-age`.

#### Cloudflare-readiness deltas

`caddy/Caddyfile.prod` includes a commented `trusted_proxies cloudflare`
snippet — uncomment it once Cloudflare orange-cloud is enabled so Caddy
honors `CF-Connecting-IP`. Direct Let's Encrypt issuance is documented in
that same file as an opt-in for self-contained deploys.

### Appliku (gunicorn + WhiteNoise)

The existing Appliku flow is preserved as an additive deploy target.
`collectstatic` aggregates the SPA bundle into `STATIC_ROOT`; WhiteNoise
serves it; the catch-all `spa_shell` view returns `index.html` for any
non-API/non-admin path.

1. Push the repo to GitHub.
1. Add an Application in Appliku and attach a Postgres database.
1. Application Settings > Volumes:
    - Container path: `/volumes/media`
    - URL: `/media/`
    - Environment variable: `MEDIA`
    - Add volume
1. Application Settings > Processes:
    - `web`: `bash web.sh`
    - `release`: `bash release.sh`
1. Application Settings > Build Settings:
    - Base Docker Image: `Dockerfile from the codebase`
    - Dockerfile path: `Dockerfile` (target: `app`)
1. Application Settings > Environment Variables:
    - `ALLOWED_HOSTS` (e.g. `{{ cookiecutter.project_slug }}.applikuapp.com`)
    - `CSRF_TRUSTED_ORIGINS` (e.g. `https://{{ cookiecutter.project_slug }}.applikuapp.com`)
    - `SECRET_KEY`
    - `DATABASE_URL` (provisioned)
