# 0004 — Appliku is the single deployment target

## Context

Every generated project deploys to **Appliku**, a managed PaaS that reads
`appliku.yml` and provisions Postgres, Redis, and web/worker/release
processes, env, and TLS. Push to `main` and the platform redeploys.

## Decision

The template ships one deployment configuration: `appliku.yml`.

The shared `Dockerfile` has no `CMD`; the orchestrator picks the entry
point (`./web.sh`, `./worker.sh`, or `./release.sh`). Migrations and
one-shot tasks belong in `release.sh`, not `web.sh`, and Appliku invokes
`release.sh` as its managed `release` process, declared in `appliku.yml`.

## Consequences

Positive:

- One deployment surface to keep coherent. Adding a process (e.g. a
  `beat` process for scheduled jobs) touches `appliku.yml` only.
- The CMD-less Dockerfile pattern keeps `web.sh`/`worker.sh` as the
  documentation of how each process starts.

Negative:

- A project that needs to run outside Appliku has no template-provided
  path and has to build one from scratch.
