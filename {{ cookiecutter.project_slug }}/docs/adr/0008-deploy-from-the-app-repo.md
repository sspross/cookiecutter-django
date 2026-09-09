# 0008 - Deploy from the app repo

## Context

A compose deployment on a plain docker host needs someone to pull the image,
write the `.env`, run the migrations and recreate the containers. When a
separate infra repo owned that, a release was a tag here, a pin bump there and
a manual run with the operator's credentials; every app change that touched an
environment variable took two pull requests.

The deploy belongs to the app: the compose file mirrors the app's topology, the
secrets are the app's, and the person merging a change is the one who wants to
ship it.

## Decision

**This repo owns its production deployment on a docker host.** Whoever runs the
host provides a contract, and nothing else:

- a docker host reachable over SSH as a user in the `docker` group, either
  through a tailnet (Tailscale SSH, no key) or over a public address with a
  deploy key
- a reverse proxy on the docker network `ingress` that proxies the app's
  hostname to `{{ cookiecutter.project_slug }}-web:8000`, terminates TLS and
  forwards `X-Forwarded-Proto`
- named volumes that survive: nothing on the host prunes them

The app side, all in this repo:

- **`compose.prod.yaml`** is the production manifest: the image pinned to a
  GHCR tag, `web` on the `ingress` network under the alias
  `{{ cookiecutter.project_slug }}-web` instead of a published port, the
  compose project named after the project so the volumes keep their identity,
  otherwise the topology of `compose.yaml`. Nothing is pinned in it that a
  deploy should be able to toggle; `DEBUG`, `SENTRY_DSN` and
  `CSRF_TRUSTED_ORIGINS` come from `.env`.
- **Images are tagged by commit.** Every push to `main` builds and pushes
  `ghcr.io/<owner>/<repo>:<sha>` and `:latest` (`image.yml`), one plain
  manifest per tag. The same workflow keeps only the newest 10 versions,
  because GHCR never expires versions and private packages count against the
  owner's quota.
- **The deploy is a button.** `deploy.yml` runs on `workflow_dispatch`, only
  on `main`, one at a time (`concurrency`). A GitHub-hosted runner drives the
  host's docker daemon over `DOCKER_HOST=ssh://<DEPLOY_HOST>`. Compose runs on
  the runner, so nothing is copied to the host and no checkout or stack
  directory exists there.
- **Repository secrets and variables are the production environment.** The
  workflow writes every repository variable and every secret into `.env`
  verbatim and logs the key names. Adding a setting is "add it in the repo
  settings, click deploy"; removing it and deploying again reverts. Values
  persist until removed. Excluded are `GITHUB_TOKEN` and the deploy plumbing,
  recognisable by prefix: `DEPLOY_*` (`DEPLOY_HOST`, `DEPLOY_URL`,
  `DEPLOY_TAILNET_TAG`, `DEPLOY_SSH_PRIVATE_KEY`) and `TS_OAUTH_*`.
- **A deploy is gated on health.** `docker compose up --wait` fails when
  `release` exits non-zero or `web` never becomes healthy; with `DEPLOY_URL`
  set, a request to `<DEPLOY_URL>/healthz` through the reverse proxy has to
  answer 200. On failure the workflow prints the container logs.

Private repositories on GitHub Free have no environments, so secrets and
variables live at the repository level and the `main` restriction is a
condition in the job, not a GitHub setting. On GitHub Team the job gets
`environment: production`, the secrets and variables move into that
environment, and required reviewers become an option. Nothing else changes.

## Consequences

Positive:

- One pull request per change, whether it touches code, the compose topology
  or an environment variable.
- Every commit on `main` is deployable and identifiable by its sha, in the
  registry and in the running container. Rollback is deploying an older
  state of `main`.
- No credentials on the host beyond what it had, and no persistent runner
  there. With a tailnet, the node the deploy uses exists for the length of
  the job.

Negative:

- The deploy credential in the repository (`DEPLOY_SSH_PRIVATE_KEY`, or the
  `TS_OAUTH_*` pair) is the key to the host: whoever holds it can reach the
  docker daemon, which is root-equivalent there.
- `compose.yaml` and `compose.prod.yaml` have to stay coherent when the
  topology changes, the same way `appliku.yml` does (ADR-0004).
- The deploy waits for the image workflow of the same commit. Pressing the
  button too early fails with a clear message and has to be repeated.
- A migration that fails leaves the previous `web` and `worker` running on the
  old image against a partially migrated schema; see `docs/OPERATIONS.md`.
