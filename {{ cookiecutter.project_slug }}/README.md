## Setup

- `uv sync`
- `uv run pre-commit install`
- `uv run playwright install chromium`
- `make db.recreate`
- `make db.initialize`
- `make frontend.install`

## Work

- Start frontend watcher first: `make frontend.dev`
- `uv run python manage.py runserver`

## Add your own app(s)

- `uv run python manage.py startapp xyz`

## Stage Deployment

### Docker with Caddy

#### Install

- `uv add fabric`
- Adjust `TARGET_SERVER` and `TARGET_DIR` in `fabfile.py`
- Clone project manually to the `TARGET_DIR` on `TARGET_SERVER`
- Choose an unused port in `docker-compose.yml`, e.g. `"8123:8000"`
- Add `{{ cookiecutter.project_slug }}.intra.sspross.ch` to `ALLOWED_HOSTS` in `docker-compose.yml`
- Add proxy rule to intra Caddy `~/projects/caddy-intra/Caddyfile`:
```
{{ cookiecutter.project_slug }}.intra.sspross.ch {
    reverse_proxy http://smini.tail9af27c.ts.net:8123
}
```
- Restart intra Caddy `docker compose down && docker compose up -d`

#### Deploy

- Run `uv run fab deploy` and if needed `uv run fab migrate`
- Visit https://{{ cookiecutter.project_slug }}.intra.sspross.ch

### Appliku (outdated)

1. Push Repo on GitHub
1. Add Application, e.g. `{{ cookiecutter.project_slug }}` to Appliku: https://app.appliku.com/dashboard/team/private/applications
1. Add Postgres Database to new Application
1. Open Application Settings > Volumes:
    1. Container path: `/volumes/media`
    1. URL: `/media/`
    1. Envirnment variable: `MEDIA`
    1. Add volume
1. Open Application Settings > Processes:
    1. Add `web`: `bash web.sh`
    1. Add `release`: `bash release.sh`
1. Open Application Settings > Build Settings:
    1. Base Docker Image: `Dockerfile from the codebase`
    1. Dockerfile path: `./code/Dockerfile`
    1. Dockerfile context path: `../`
    1. Save changes
1. Open Application Settings > Environment Variables and add:
    1. ALLOWED_HOSTS (e.g. `{{ cookiecutter.project_slug }}.applikuapp.com`)
    1. CSRF_TRUSTED_ORIGINS (e.g. `https://{{ cookiecutter.project_slug }}.applikuapp.com`)
    1. SECRET_KEY (`python -c "import random, string; print(''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(50)))"`)
    1. DATABASE_URL (should already be there)
    1. Save and deploy
