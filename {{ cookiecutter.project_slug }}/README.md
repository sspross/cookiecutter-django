# {{ cookiecutter.project_name }}

## Development

### Requirements

- `uv` (https://docs.astral.sh/uv/)
- Docker Engine 25 or newer with Compose 2.24.4 or newer, for `make up`
- Local Redis Server for `make test`, whose worker tests perform a real job: `brew install redis`

Run `make doctor` to check the Docker setup of this machine. It prints one line
per check and the fix for each failed one.

When Docker's data directory is on btrfs (OrbStack Linux machines) and image
builds fail in `apt-get install`, put
`{"features": {"containerd-snapshotter": false}, "storage-driver": "btrfs"}`
into `/etc/docker/daemon.json` and restart Docker. Existing images and volumes
are hidden after the restart.

### Setup

Run once after generating the project, in this order. The generator already
wrote `.env` with a fresh `SECRET_KEY`; a later clone starts with
`cp .env.example .env` and skips the `git init` and commit steps.

- `uv sync` (creates `uv.lock`)
- `make frontend.install` (creates `core/frontend/package-lock.json`)
- Put the project under version control, lockfiles included. The image build
  and CI install from them (`uv sync --frozen`, `npm ci`) and fail without them:
  - `git init`
  - `git add --all`
  - `git commit -m "Initial setup from django project template"`
- `uv run pre-commit install`
- `uv run playwright install chromium`
- `make up` (builds the image and starts the stack, see [Work](#work))

### Google login

Optional. The first Google login of an email in `SSO_SUPERUSER_EMAILS`
creates the superuser.

1. In the Google Cloud console, go to APIs & Services > Credentials and
   create an OAuth client of type "Web application".
2. Add the redirect URIs
   `http://localhost:8000/accounts/google/login/callback/` and
   `https://<domain>/accounts/google/login/callback/`. Google accepts only
   registered redirect URIs, so login works on port 8000 only. `make up` uses
   another port when 8000 is taken. Register that port's URI by hand to use it.
3. Set `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET` in `.env`.
4. To let anyone besides the author sign in, set `SSO_ALLOWED_DOMAINS`,
   `SSO_ALLOWED_EMAILS` and `SSO_SUPERUSER_EMAILS` (see "SSO allowlist" in
   `CONTEXT.md`).
5. Run `make up`. If it prints port 8000, log in at `/accounts/login/` with
   "Sign in with Google".

### Work

- `make up` builds the image, starts Postgres, Redis, the release step, web and
  worker, waits until the app is healthy and prints the URL and the login
  (`admin` / `admin`). It uses port 8000, or the next free port when 8000 is
  taken. Each worktree has its own stack and data, so several can run at once.
  A code change needs another `make up`.
- `make logs` follows the logs of this worktree's stack.
- `make down` stops the stack and keeps its data.
- `make destroy` stops the stack and deletes its volumes and image. Run it
  before removing a worktree.
- `make doctor` checks the Docker setup of this machine.
- `.env` is optional. When it exists, its values are loaded, but the local
  stack overrides `DEBUG`, `DATABASE_URL` and `REDIS_URL`.

### Tests

- `make test` — pytest suite (native, needs `uv` and a local Redis)
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
image without pushing it, so a broken `Dockerfile` or a `package-lock.json`
out of sync with `package.json` fails CI.

Appliku ignores that image and deploys on every push to `main`; a compose host
that deploys `compose.yaml` from git builds the checked-out commit. Only the
`deploy` workflow runs the published image.

### Appliku

`appliku.yml` is the source of truth for this target. Push to `main`; Appliku
redeploys and runs `release.sh` automatically.

First-time setup:

1. Push the repo to GitHub.
2. Create the application in Appliku, pointed at the repo.
3. Appliku reads `appliku.yml` and provisions the web/worker/release processes,
   Postgres database, and Redis instance.
4. Set `SECRET_KEY` in Appliku's environment variables (one-time):
   `python -c "import secrets; print(secrets.token_urlsafe(50))"`
5. Add a domain in Appliku; `ALLOWED_HOSTS` is auto-populated from `from_domains: true`.
6. Set the [Google login](#google-login) variables.
7. Deploy.
8. Create the first superuser, see "First superuser" in `docs/OPERATIONS.md`.

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
4. Create the first superuser, see "First superuser" in `docs/OPERATIONS.md`.
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
   Optional: the [Google login](#google-login) variables, with
   `GOOGLE_OAUTH_CLIENT_SECRET` as a secret.
3. Merge to `main`, wait for the `image` workflow, run `deploy`.
4. Create the first superuser, see "First superuser" in `docs/OPERATIONS.md`.

Any further variable or secret is a production setting: add `SENTRY_DSN` or
`DEBUG=true`, deploy; remove it, deploy. Names starting with `DEPLOY_` and
`TS_OAUTH_` are the workflow's own and never reach the stack.

`docs/OPERATIONS.md` is the runbook: environment variables, health probing, logs, backups, troubleshooting.
