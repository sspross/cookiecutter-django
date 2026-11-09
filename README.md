# Django Project Template

## Usage

### Requirements

Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Create new Django Project from this template

Use this single command to create a new project from this template:
```bash
uv run --with cookiecutter python -m cookiecutter https://github.com/sspross/cookiecutter-django.git
```

## Working on this template

- Run `make test` to verify if using the template still works as expected. It
  needs Docker and ports 8000 and 8001 free, because it runs the generated
  project's `make up` for two stacks side by side.
