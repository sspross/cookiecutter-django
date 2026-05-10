# {{ cookiecutter.project_slug }}

See `CONTEXT.md` for domain language and `docs/adr/` for past architectural decisions.

## Guardrails

Run these before declaring work complete:

- `make test` — run the test suite; nothing ships if this is red.
- `make lint` — static checks.
- `make format` — apply formatting.
- `make precommit` — run the full pre-commit pipeline locally to catch issues before committing.

## Agent skills

### Issue tracker

Issues live in GitHub Issues at `{{ cookiecutter.django_username }}/{{ cookiecutter.project_slug }}`, accessed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

Agents are authorized to use the `gh` CLI to read, comment on, label, open, and close issues and pull requests in this repo without asking first. Force-pushes, branch deletions, repo-settings changes, releases, workflow dispatches, and secret access still require explicit user confirmation.

### Triage labels

Canonical triage label names (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) — no overrides. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
