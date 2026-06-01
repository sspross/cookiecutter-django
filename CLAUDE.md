## Keeping generated-project skills in sync

When changing the default template stack — adding/removing an app under `{{ cookiecutter.project_slug }}/`, swapping the async runner, changing the deploy target, adding/retiring an ADR, etc. — also update the **Template baseline** section in `{{ cookiecutter.project_slug }}/.claude/skills/architecture-overview/SKILL.md` so the onboarding artifact in generated projects keeps subtracting the right scaffolding.
