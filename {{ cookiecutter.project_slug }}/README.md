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
  non-API/non-admin/non-static path. WhiteNoise inside the `app` container
  serves the hashed Vite + admin assets with the right cache headers.

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
make dev.up       # Postgres in docker compose
make dev.django   # Django on the host (127.0.0.1:8000)
make dev.vite     # Vite dev server on the host (localhost:5173)
```

Open the SPA at `http://localhost:5173`. Vite's dev-server proxy forwards
`/api`, `/admin`, `/media`, and `/static` to Django on `127.0.0.1:8000`, so
the browser sees one origin and cookies, CSRF, and `SameSite` behave the
way they will in production. `/static` is included so Django admin's CSS
and JS render under `DEBUG=True`. To tear everything down: `make dev.down`.

### Removing the `example` app

The `example` app ships as a complete CRUD demo (`Tag`, `Project`, `Task`)
that exists only to show the layering pattern. It's designed to be
removable — taking it out leaves the walking skeleton (health, config,
SPA shell) intact and clean. Two edits:

1. Drop `"example"` from `INSTALLED_APPS` in `core/settings/base.py`.
2. Remove the `api.add_router("/example", "example.api.router")` line in
   `core/api.py`.

After those edits, the project boots, `/api/health` and `/api/config`
still respond, and the SPA's `/` route still renders. You can also
delete the `example/` directory and its routes/components on the
frontend.

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

Both supported deploy paths ship the same `app` container (gunicorn +
WhiteNoise), differing only in where it runs and what terminates TLS.
WhiteNoise serves hashed Vite + admin assets with the right cache
headers; the catch-all `spa_shell` view returns `index.html` for any
non-API/non-admin path; media is served by the operator's reverse proxy
from a bind-mounted volume (not by Django).

### Docker compose on a VM

Bring up `app` + `postgres` and expose the gunicorn port on the host:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Point your own reverse proxy (Caddy, nginx, Cloudflare Tunnel, etc.) at
the exposed `app` port. A copy-pasteable Caddyfile for the host:

```caddy
example.com {
    encode zstd gzip

    # Media is served by Caddy directly from a bind-mount of the
    # `media_data` named volume (write side stays on the `app` service).
    handle /media/* {
        root * /var/lib/docker/volumes/<stack>_media_data/_data
        file_server
    }

    # Everything else goes to gunicorn. `header_up Host {host}` keeps
    # Django's ALLOWED_HOSTS check happy.
    reverse_proxy 127.0.0.1:8000 {
        header_up Host {host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

- `example.com` triggers Caddy's automatic Let's Encrypt issuance.
  Behind another TLS terminator (Cloudflare, an outer Caddy), bind to
  `:80` instead and let the edge handle certs.
- Behind Cloudflare with orange-cloud enabled, add a
  `servers { trusted_proxies cloudflare }` block at the top of the
  Caddyfile so logs and rate-limit logic see the real client IP.
- Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` via env when bringing up
  the stack (e.g. `ALLOWED_HOSTS=example.com docker compose -f ... up -d`).

### Appliku

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
