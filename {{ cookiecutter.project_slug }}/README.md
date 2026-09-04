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
- `uv run pre-commit install`
- `uv run playwright install chromium`
- `make db.recreate` (Postgres only — skip if using SQLite)
- `make db.initialize`
- `make frontend.install`

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

`appliku.yml` is the single source of truth. Push to `main`; Appliku redeploys
and runs `release.sh` automatically.

First-time setup:

1. Push the repo to GitHub.
2. Create the application in Appliku, pointed at the repo.
3. Appliku reads `appliku.yml` and provisions the web/worker/release processes,
   Postgres database, and Redis instance.
4. Set `SECRET_KEY` in Appliku's environment variables (one-time):
   `python -c "import secrets; print(secrets.token_urlsafe(50))"`
5. Add a domain in Appliku; `ALLOWED_HOSTS` is auto-populated from `from_domains: true`.
6. Deploy.

See [docs.appliku.com/docs/cli-sdk](https://docs.appliku.com/docs/cli-sdk/) for the Appliku CLI/SDK reference.
