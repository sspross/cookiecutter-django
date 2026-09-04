# 0004 - Two deployment targets over one deployment contract

## Context

Generated projects do not all land on the same infrastructure. Some deploy to
**Appliku**, a managed PaaS that reads `appliku.yml` and provisions Postgres,
Redis, web/worker/release processes, env, and TLS. Others deploy as a
docker-compose compatible stack: a Docker host behind a reverse proxy, or a PaaS
that deploys a compose file straight from git (Dokploy, Coolify).

Two independent deployment descriptions drift apart. Two manifests over a
shared contract keep the drift confined to the part that genuinely differs per
platform.

## Decision

The template ships one **deployment contract** and two manifests that consume
it.

The contract is the part the app owns, identical on both targets:

- A `Dockerfile` building one image, running as the non-root `app` user. Its
  `CMD` is `./web.sh`, so an orchestrator that cannot override the command still
  gets a serving web process; every orchestrator that can override it picks the
  entry point per process instead.
- Three process scripts: `web.sh` (gunicorn, bound to `0.0.0.0:${PORT:-8000}`),
  `worker.sh` (the forking RQ worker), `release.sh`.
- `/healthz`, an anonymous JSON probe returning 200 when Postgres and Redis both
  answer and 503 otherwise.
- Settings driven entirely by environment variables (`core/settings/base.py`),
  so nothing about a host is baked into the image.

**Migrations and one-shot tasks belong in `release.sh`**, not in `web.sh`.
`release.sh` runs once per deploy, before web and worker start, on both targets.

The two manifests:

- `appliku.yml` declares the `web`, `worker` and `release` processes, the
  managed `db` and `redis` databases, the `media` volume, and the environment
  wiring Appliku injects.
- `compose.yaml` declares the same topology for a docker-compose compatible
  host: `db` (postgres:17) and `redis` (redis:7) services with healthchecks,
  a `release` service that runs to completion, `web` and `worker` on the same
  built image, named volumes for Postgres data, Redis data and media, and the
  web port published on loopback only.

Host provisioning, the reverse proxy and TLS termination are outside the
template. `compose.yaml` publishes `127.0.0.1:8000` and expects something in
front of it to terminate TLS and forward `X-Forwarded-Proto`, which
`SECURE_PROXY_SSL_HEADER` trusts.

### Releases and the image

A release is a semver git tag on `main`. The `image` workflow builds the
`Dockerfile` on that tag and pushes it to GHCR, so a deployable artefact exists
outside the git history. Appliku ignores tags and builds from `main` itself.
`docs/OPERATIONS.md` holds the flow.

### When an infra repo owns production

A compose deployment can be driven from a separate infra repo instead of from
this one. That repo owns the production compose file and everything around it:
the pinned GHCR image tag, the ingress network, the volumes, the restart policy
and the secrets. It is deployed with its own tooling, and a version bump there
is a change of the pinned tag.

The image is the contract between the two repos: this repo produces tagged
images, the infra repo consumes one.

In that setup `compose.yaml` here keeps two roles. It stays the manifest for
hosts that deploy compose straight from git (Dokploy, Coolify), and it is the
reference shape the infra repo copies from: replace `build: .` with the pinned
image, drop the published `ports` and join the ingress network instead, and keep
the rest of the topology (the `release` service ordering, the healthchecks, the
volumes) as it is here.

## Consequences

Positive:

- A project picks its target without rewriting how it boots. The contract is
  the same either way, so a move from one target to the other is a manifest
  swap.
- The process scripts stay the documentation of how each process starts,
  readable without knowing either platform, while the `CMD` default keeps the
  image runnable on a host that only knows how to start one container.

Negative:

- Both manifests have to stay coherent when the topology changes. Adding a
  process (a `beat` process for scheduled jobs, say) or a backing service means
  editing `appliku.yml` **and** `compose.yaml`, and a project that only uses one
  of them will not notice the other rotting.
- Neither manifest covers the host itself. A compose deployment still needs
  someone to provision the machine, the proxy and the certificates.
- With an infra repo in front, an app change that needs a new environment
  variable or a new process takes two pull requests: one here, one there. They
  land in that order, and the app has to boot with the variable still missing
  until the second one is deployed.
