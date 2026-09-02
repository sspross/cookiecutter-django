# 0004 — Two deployment paths ship: Appliku canonical, Docker Compose self-host

Status: Accepted

## Context

Past projects from this template have deployed two ways:

1. **Appliku** — a managed PaaS that reads `appliku.yml` and provisions
   Postgres, Redis, web/worker/release processes, env, and TLS. Push to
   `main` and the platform redeploys.
2. **Self-host on a Mac mini behind Caddy + Tailscale** — a `fabfile.py`
   that pulls the repo, rebuilds the image, and brings the
   docker-compose stack up. Useful for internal tools that should not
   leave the home/office network.

Both paths are real for the maintainer; picking one and removing the
other has been re-litigated and re-reverted enough times to merit
freezing the answer.

## Decision

The template ships **both** deployment configurations:

- `appliku.yml` — the canonical path. README leads with Appliku.
- `docker-compose.yml` + `fabfile.py` — the self-host fallback.

Both produce identical web + worker + redis + postgres topologies. The
shared `Dockerfile` has no `CMD`; the orchestrator picks the entry
point (`./web.sh`, `./worker.sh`, or `./release.sh`).

`release.sh` is invoked:

- by Appliku as a managed `release` process (declared in `appliku.yml`).
- by the self-host path via `docker compose run --rm web ./release.sh`,
  wrapped in `fab release`.

Migrations and one-shot tasks belong in `release.sh`, not `web.sh`.

## Consequences

Positive:

- A new project can be production-deployable in 30 minutes (Appliku) or
  self-hosted on existing Mac mini infra in an hour, without rewriting
  config.
- The CMD-less Dockerfile pattern keeps `web.sh`/`worker.sh` as the
  documentation of how each process starts; no compose-vs-Dockerfile
  divergence.

Negative:

- Two deployment surfaces means two failure modes a developer might
  hit. Most of the time only one is in use.
- Both files have to stay coherent if topology changes (e.g. adding
  a `beat` process for scheduled jobs would touch both).

## Alternatives considered

- **Ship only `appliku.yml`.** Rejected — the self-host path is in
  active use and re-creating it from scratch each time is wasteful.
- **Ship only `docker-compose.yml`.** Rejected — Appliku is the
  canonical path for projects that should be on the open internet, and
  re-deriving `appliku.yml` from compose loses the volume / database /
  domain wiring that the platform does for free.
- **Hide one behind a cookiecutter question.** Rejected — both paths
  are small (a single yml + a fabfile) and the cost of always shipping
  both is lower than the cost of asking the user to decide upfront.
