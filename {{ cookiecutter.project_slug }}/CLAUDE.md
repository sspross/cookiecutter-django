# {{ cookiecutter.project_slug }}

See `CONTEXT.md` for domain language, `docs/adr/` for the architectural decisions in effect, and `docs/OPERATIONS.md` for the production runbook.

## Guardrails

Run these before declaring work complete:

- `make test` — run the test suite; nothing ships if this is red.
- `make lint`: static checks.
- `make format` — apply formatting.
- `make precommit`: full pre-commit pipeline. Together with `make lint` it covers every static check CI runs.

## Conventions

- **Python tooling is `uv`** — `uv add`, `uv run`, etc. Never `pip`.
- **Outside a `TYPE_CHECKING` guard, defer an import only for a genuine circular cycle.** Add `# noqa: PLC0415` and a comment naming the cycle, e.g. `# avoid circular: jobs → services → models → jobs`.
- **A `TYPE_CHECKING` import may cross a `tach` boundary for type hints, but must follow the runtime arrow.** See ADR-0005.
- **Put units in names** — `TIMEOUT_SECONDS`, `MAX_SIZE_MB`, `DELAY_MS`.
- **While iterating run only the tests you touched; run the full suite once at the end.**
- **Never `--no-verify`, and never skip or delete a failing test to go green** — fix the underlying problem.
- **After 3 failed attempts at the same problem, stop and reassess** instead of repeating variations.

## Agent skills

### Issue tracker

Issues live in GitHub Issues at `{{ cookiecutter.github_owner }}/{{ cookiecutter.project_slug }}`, accessed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

Agents are authorized to use the `gh` CLI to read, comment on, label, open, and close issues and pull requests in this repo without asking first. Force-pushes, branch deletions, repo-settings changes, releases, workflow dispatches, and secret access still require explicit user confirmation.

### Triage labels

Canonical triage label names (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) — no overrides. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
