# {{ cookiecutter.project_name }}

## Development

### Requirements

- `uv` (https://docs.astral.sh/uv/)
- (Optional) Local Postgres Server, if SQLite is not enough
- (Optional) tmux for `make dev` experience: `brew install tmux`
- Local Redis Server for the async worker and for `make test`, whose worker tests perform a real job: `brew install redis`

### Setup

Run once after generating the project, in this order. Later clones skip the
`git init` and commit steps.

- `cp .env.example .env`
- `uv sync` (creates `uv.lock`)
- `make frontend.install` (creates `core/frontend/package-lock.json`)
- Put the project under version control, lockfiles included. The image build
  and CI install from them (`uv sync --frozen`, `npm ci`) and fail without them:
  - `git init`
  - `git add --all`
  - `git commit -m "Initial setup from django project template"`
- `uv run pre-commit install`
- `uv run playwright install chromium`
- `make db.recreate` (Postgres only, skip if using SQLite)
- `make db.migrate`
- Create the first superuser: turn on Google login (see
  [Google login](#google-login)), or run `uv run ./manage.py createsuperuser`.

### Google login

Optional. The first Google login of {{ cookiecutter.author_email }} creates
the superuser.

1. In the Google Cloud console, go to APIs & Services > Credentials and
   create an OAuth client of type "Web application".
2. Add the redirect URIs
   `http://localhost:8000/accounts/google/login/callback/` and
   `https://<domain>/accounts/google/login/callback/`.
3. On the OAuth consent screen, pick "Internal" for a Workspace-only
   audience. Pick "External" for private Gmail accounts, and publish the app:
   while it is in "Testing", only the listed test users can sign in.
4. Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` in `.env`.
5. To let anyone besides the author sign in, set `SSO_ALLOWED_DOMAINS`,
   `SSO_ALLOWED_EMAILS` and `SSO_SUPERUSER_EMAILS` (see `.env.example`).
6. Restart `make backend.dev` and log in at
   http://localhost:8000/accounts/login/ with "Sign in with Google".

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

Three targets are supported, all on the same image and the same process
scripts (`web.sh`, `worker.sh`, `release.sh`): Appliku, a compose host that
builds from git, and a docker host this repo deploys to with a button. See
ADR-0004 and ADR-0008.

### Release

Every push to `main` is a release. The `image` workflow builds `Dockerfile`
on that commit and pushes `ghcr.io/<owner>/<repo>:<sha>` and `:latest`, then
prunes the package to the newest 10 versions. Pull requests build the same
image without pushing it, so a broken `Dockerfile` or a stale lockfile fails
CI.

Appliku ignores that image and deploys on every push to `main`; a compose host
that deploys `compose.yaml` from git builds the checked-out commit. Only the
`deploy` workflow runs the published image.

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
6. Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` (the OAuth
   client from Development > Google login, with the production redirect URI
   registered), plus `SSO_ALLOWED_DOMAINS` / `SSO_ALLOWED_EMAILS` /
   `SSO_SUPERUSER_EMAILS` if anyone besides the author signs in with Google.
7. Deploy.
8. Log in with Google as {{ cookiecutter.author_email }}. Both email lists
   default to the author email, so this first Google login creates the first
   superuser. Without Google
   login, use the `createsuperuser` fallback in `docs/OPERATIONS.md`,
   "First superuser".

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
4. Create the first superuser: set the Google variables in `.env` and log in
   with Google as {{ cookiecutter.author_email }}, as in the Appliku section.
   Without Google login:
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

### Docker host, deployed from this repo

`compose.prod.yaml` is the manifest for a docker host that this repo deploys
to itself: the `deploy` workflow (Actions tab, "Run workflow" on `main`)
pulls the image of that commit on the host, runs `release`, recreates `web`
and `worker`, and checks `/healthz`. Nothing is copied to the host; the
repository's Actions secrets and variables are the production environment
and land in the stack's `.env` on every deploy.

The host has to provide (whoever runs it, an infra repo or a person):

- SSH access for the workflow as a user in the `docker` group. Either the
  host is in a tailnet with Tailscale SSH enabled for a tag the workflow may
  join with, or it is reachable on a public address with a deploy key.
- A reverse proxy on the docker network `ingress` (`docker network create
  ingress`) that proxies the app's hostname to
  `{{ cookiecutter.project_slug }}-web:8000`, terminates TLS and forwards
  `X-Forwarded-Proto`.

First-time setup in the repository settings (Secrets and variables > Actions):

1. Variables: `DEPLOY_HOST` (`user@host`), `ALLOWED_HOSTS` (the domain, the
   compose file adds `localhost`), `CSRF_TRUSTED_ORIGINS`
   (`https://<domain>`). Optional: `DEPLOY_URL` (`https://<domain>`, turns on
   the smoke test), `DEPLOY_TAILNET_TAG` (`tag:<something>`, makes the job
   join the tailnet as `<something>-{{ cookiecutter.project_slug }}`).
2. Secrets: `SECRET_KEY`
   (`python -c "import secrets; print(secrets.token_urlsafe(50))"`),
   `POSTGRES_PASSWORD` (URL-safe). Without a tailnet: `DEPLOY_SSH_PRIVATE_KEY`, the
   private half of the deploy key. With a tailnet: `TS_OAUTH_CLIENT_ID` and
   `TS_OAUTH_SECRET` of an OAuth client that may mint keys for the tag
   (org-level secrets shared with the repo work too).
   For Google login: variable `GOOGLE_OAUTH_CLIENT_ID`, secret
   `GOOGLE_OAUTH_CLIENT_SECRET`, and optional variables
   `SSO_ALLOWED_DOMAINS` / `SSO_ALLOWED_EMAILS` / `SSO_SUPERUSER_EMAILS`.
3. Merge to `main`, wait for the `image` workflow, run `deploy`.
4. Log in with Google as {{ cookiecutter.author_email }}, which creates the
   first superuser. Without Google login, from a device that may SSH to the
   host:
   `DOCKER_HOST=ssh://<DEPLOY_HOST> docker exec -it {{ cookiecutter.project_slug }}-web-1 uv run ./manage.py createsuperuser`

Any further variable or secret is a production setting: add `SENTRY_DSN` or
`DEBUG=true`, deploy; remove it, deploy. Names starting with `DEPLOY_` and
`TS_OAUTH_` are the workflow's own and never reach the stack.

`docs/OPERATIONS.md` is the runbook: environment variables, health probing, logs, backups, troubleshooting.
