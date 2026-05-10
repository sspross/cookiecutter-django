# {{ cookiecutter.project_name }}

## Development

### Requirements

- Local Redis Server
- (Optional) Local Postgres Server, if SQLite is not enough
- `uv` (https://docs.astral.sh/uv/)

### Setup

- `cp .env.example .env` (already done by post_gen_project.py)
- `uv sync`
- `uv run pre-commit install`
- `uv run playwright install chromium`
- `make db.recreate` (Postgres only — skip if using SQLite)
- `make db.initialize`
- `make frontend.install`

### Work

- Start frontend watcher first: `make frontend.dev`
- `uv run python manage.py runserver`
- Log in at http://localhost:8000/accounts/login/ with `{{ cookiecutter.django_username }}` / `{{ cookiecutter.django_password }}`

### Tests

- `make test` — pytest suite
- `make test.live.watch` — live Playwright tests, headed + slowmo (debugging)
- `make precommit` — full pre-commit pipeline

### Frontend type generation

After adding/changing ninja API endpoints, regenerate the SPA's typed schema:

- `uv run python manage.py runserver` (in another terminal)
- `make schema`

## Deployment

This template ships configurations for two deployment paths. Pick one.

### Appliku (canonical)

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

See `.claude/skills/appliku/SKILL.md` for the full Appliku CLI/SDK reference.

### Docker Compose (self-host, e.g. Mac mini via Tailscale)

For a Mac mini hosted behind Caddy + Tailscale:

1. `uv add fabric` (if not already)
2. Adjust `TARGET_SERVER` and `TARGET_DIR` in `fabfile.py`.
3. Clone the repo to `TARGET_DIR` on the host.
4. Pick an unused port in `docker-compose.yml`'s `ports` mapping.
5. Add your hostname to `ALLOWED_HOSTS` in `docker-compose.yml`.
6. Add a Caddy proxy rule.
7. Deploy: `uv run fab deploy && uv run fab release`.
