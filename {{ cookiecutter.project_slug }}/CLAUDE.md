# {{ cookiecutter.project_slug }}

See `CONTEXT.md` for domain language and `docs/adr/` for past architectural decisions.

## Guardrails

Run these before declaring work complete:

- `make test` — run the test suite; nothing ships if this is red.
- `make lint` — static checks.
- `make format` — apply formatting.
- `make precommit` — run the full pre-commit pipeline locally to catch issues before committing.

## Conventions

- **Python tooling is `uv`** — `uv add`, `uv run`, etc. Never `pip`.
- **Imports go at module top.** Defer one only for a genuine circular cycle (add a comment naming it, e.g. `# avoid circular: jobs → services → models → jobs`) or under a `TYPE_CHECKING` guard. Judge each import on its own; `# noqa: PLC0415` is a smell, not a pattern to copy.
- **Type-hint everything.** Annotate all function signatures and any non-obvious variable; the goal is maximal coverage, not just the easy cases.
- **Put units in names** — `TIMEOUT_SECONDS`, `MAX_SIZE_MB`, `DELAY_MS`.
- **No TODOs without an issue number.**
- **Never `--no-verify`, and never skip or delete a failing test to go green** — fix the underlying problem.
- **After 3 failed attempts at the same problem, stop and reassess** instead of repeating variations.

## Agent skills

### Issue tracker

Issues live in GitHub Issues at `{{ cookiecutter.django_username }}/{{ cookiecutter.project_slug }}`, accessed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

Agents are authorized to use the `gh` CLI to read, comment on, label, open, and close issues and pull requests in this repo without asking first. Force-pushes, branch deletions, repo-settings changes, releases, workflow dispatches, and secret access still require explicit user confirmation.

### Triage labels

Canonical triage label names (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) — no overrides. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
