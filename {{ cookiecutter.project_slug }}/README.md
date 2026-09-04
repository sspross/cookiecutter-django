# {{ cookiecutter.project_name }}

## Development

### Requirements

- `uv` (https://docs.astral.sh/uv/)
- (Optional) Local Postgres Server, if SQLite is not enough
- (Optional) tmux for `make dev` experience: `brew install tmux`
- (Optional) Local Redis Server for async worker: `brew install redis`

### Setup

- (`cp .env.example .env`)
- `uv sync`
- `make frontend.install`
- Commit `uv.lock` and `core/frontend/package-lock.json`: the image build and
  CI install from them (`uv sync --frozen`, `npm ci`) and fail without them.
- `uv run pre-commit install`
- `uv run playwright install chromium`
- `make db.recreate` (Postgres only — skip if using SQLite)
- `make db.initialize`

### Work

- `make dev` — tmux: a shell pane + frontend/backend/worker panes
- ...or run individually in separate terminals:
  - `make frontend.dev` (start this first)
  - `make backend.dev`
  - `make worker.dev` (needs Redis; only does work once you write a job)
- Log in at http://localhost:8000/accounts/login/

### Tests

- `make test` — pytest suite
- `make test.live.watch` — live Playwright tests, headed + slowmo (debugging)
- `make precommit` — full pre-commit pipeline

### Frontend type generation

After adding/changing ninja API endpoints, regenerate the SPA's typed schema:

- `make schema` (runs offline; no server needed)

## Deployment

Two targets are supported, both on the same image and the same process scripts
(`web.sh`, `worker.sh`, `release.sh`). See ADR-0004.

### Release

A release is a semver git tag on `main`: `git tag v1.2.3 && git push origin v1.2.3`.
The `image` workflow builds `Dockerfile` on that tag and pushes
`ghcr.io/<owner>/<repo>:1.2.3` and `:latest`. Pull requests build the same image
without pushing it, so a broken `Dockerfile` or a stale lockfile fails CI.

Appliku ignores tags and deploys on every push to `main`; a compose host that
deploys `compose.yaml` from git builds the checked-out commit. Only a separate
infra repo owning the production compose file pins the published tag.

### Appliku

`appliku.yml` is the source of truth for this target. Push to `main`; Appliku
redeploys and runs `release.sh` automatically. `release.sh` only runs
migrations, so a deploy never touches account data.

First-time setup:

1. Push the repo to GitHub.
2. Create the application in Appliku, pointed at the repo.
3. Appliku reads `appliku.yml` and provisions the web/worker/release processes,
   Postgres database, and Redis instance.
4. Set `SECRET_KEY` in Appliku's environment variables (one-time):
   `python -c "import secrets; print(secrets.token_urlsafe(50))"`
5. Add a domain in Appliku; `ALLOWED_HOSTS` is auto-populated from `from_domains: true`.
6. Deploy.
7. Create the first superuser with a one-off command in Appliku:
   `uv run ./manage.py createsuperuser`. The `dumpdata.json` fixture seeds a
   local admin for `make db.initialize` only and is never loaded in production.

See [docs.appliku.com/docs/cli-sdk](https://docs.appliku.com/docs/cli-sdk/) for the Appliku CLI/SDK reference.

### Docker Compose

`compose.yaml` is the source of truth for any docker-compose compatible host: a
Docker host behind a reverse proxy, Dokploy, Coolify. It runs `db`
(Postgres 17), `redis` (Redis 7), a one-shot `release` service, `web` and
`worker`.

1. `cp .env.example .env` on the host.
2. Fill in `SECRET_KEY`, `POSTGRES_PASSWORD` (URL-safe), `ALLOWED_HOSTS` and
   `CSRF_TRUSTED_ORIGINS`. `ALLOWED_HOSTS` needs `localhost` next to the real
   domain, otherwise the `web` healthcheck gets a 400. Everything else
   (`DEBUG`, `DATABASE_URL`, `REDIS_URL`, `MEDIA_ROOT`, `MEDIA_URL`) is set by
   `compose.yaml`.
3. `docker compose up -d`. `release` runs the migrations and exits; `web` and
   `worker` start once it succeeded.
4. Create the first superuser:
   `docker compose run --rm web uv run ./manage.py createsuperuser`
5. Redeploy after a code change with `docker compose up -d --build`.

`web` publishes port 8000 on the host's loopback interface only
(`127.0.0.1:8000`). Point the reverse proxy there, or attach it to a shared
Docker network and proxy to the `web` service on port 8000. The proxy
terminates TLS, has to forward `X-Forwarded-Proto` (which
`SECURE_PROXY_SSL_HEADER` trusts) and has to strip any client-supplied one.
Uploaded media lives in the `media` volume at `/volumes/media`; Django does not
serve it with `DEBUG=false`, so point the proxy at that volume under `/media/`
if the project uses uploads.

`docs/OPERATIONS.md` is the runbook: environment variables, health probing, logs, backups, troubleshooting.
