# Django Project Template

## Requirements

Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Create new Django Project from this template

Use this single command to create a new project from this template:
```bash
uv run --with cookiecutter --with django python -m cookiecutter git@github.com:sspross/cookiecutter_django.git
```

#### Working on template

- Cleaning up `uv run pre-commit run --all-files`

#### Applying patches from projects

Basically it is possible, but most of the times it doesn't work. Files differ too much because of the replaced variables.

- In a project create a patch file for e.g. exactly one commit: `git format-patch -1 1635f19aa9ff7d694b62bef972ea2f1e036c7c86`
- Try to apply the patch here `git apply --directory=\{\{\ cookiecutter.project_slug\ \}\} path/to/0001-patch-file.patch`
