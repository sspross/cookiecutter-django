# {{ cookiecutter.project_slug }}

See `GLOSSARY.md` for domain language, `docs/ARCHITECTURE.md` for the code map, the HTML and API surfaces, the request context and the test harness, `CODING_STANDARDS.md` for review rules, `docs/adr/` for the architectural decisions in effect, and `docs/OPERATIONS.md` for the production runbook.

## Guardrails

Run these before declaring work complete:

- `make test`: run the test suite; nothing ships if this is red.
- `make lint`: static checks.
- `make format`: apply formatting.
- `make precommit`: full pre-commit pipeline. It covers every static check CI runs, all of `make lint` included.

## Test version

To let the user try your work, run `make up` and report the printed URL. It builds the image and starts an isolated stack for this worktree (login `admin` / `admin`). Run `make destroy` before removing a worktree.

## Conventions

- **Python tooling is `uv`**: `uv add`, `uv run`, etc. Never `pip`.
- **Outside a `TYPE_CHECKING` guard, defer an import only for a genuine circular cycle.** Add `# noqa: PLC0415` with the cycle named on the same line, e.g. `# noqa: PLC0415 circular: jobs → services → models → jobs`.
- **A `TYPE_CHECKING` import may cross a `tach` boundary for type hints, but must follow the runtime arrow.** See ADR-0005.
- **Put units in names**: `TIMEOUT_SECONDS`, `MAX_SIZE_MB`, `DELAY_MS`.
- **While iterating run only the tests you touched; run the full suite once at the end.**
- **Never `--no-verify`, and never skip or delete a failing test to go green**: fix the underlying problem.
- **After 3 failed attempts at the same problem, change the approach** (re-read the error, question the assumption behind the fix) instead of repeating variations.

## Agent skills

### Issue tracker

Issues live in GitHub Issues at `{{ cookiecutter.github_owner }}/{{ cookiecutter.project_slug }}`, accessed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

Agents are authorized to use the `gh` CLI to read, comment on, label, open, and close issues and pull requests in this repo without asking first. Force-pushes, branch deletions, repo-settings changes, releases, workflow dispatches, and secret access still require explicit user confirmation, with one exception: `/land` deletes, without asking, the merged ticket branches it created and the integration branch after its pull request is merged; every other branch deletion needs confirmation.

### Triage labels

Canonical triage label names (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), no overrides. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `GLOSSARY.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
