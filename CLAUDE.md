## Agent skills

### Issue tracker

Issues live in GitHub Issues on `sspross/cookiecutter_django` (uses the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo: one `CONTEXT.md` + `docs/adr/` at the root. See `docs/agents/domain.md`.

## Keeping generated-project skills in sync

When changing the default template stack — adding/removing an app under `{{ cookiecutter.project_slug }}/`, swapping the async runner, changing the deploy target, adding/retiring an ADR, etc. — also update the **Template baseline** section in `{{ cookiecutter.project_slug }}/.claude/skills/architecture-overview/SKILL.md` so the onboarding artifact in generated projects keeps subtracting the right scaffolding.
