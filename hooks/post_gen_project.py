import random
import shutil
import string
import subprocess

import click  # dependency of cookiecutter

ENV_EXAMPLE_FILE = ".env.example"
ENV_FILE = ".env"


def main():
    project_slug = "{{ cookiecutter.project_slug }}"
    secret_key = _create_django_secret_key()

    # 1. Create env file with fresh secret key
    shutil.copyfile(ENV_EXAMPLE_FILE, ENV_FILE)
    _replace_in_file(ENV_FILE, "replace-with-secret-key", secret_key)

    # 2. Update pre-commit hooks to latest versions
    _update_pre_commit_hooks()

    # 3. Print further instructions
    _print_instructions(project_slug)


def _create_django_secret_key():
    return "".join(
        random.SystemRandom().choice(string.ascii_letters + string.digits)
        for _ in range(50)
    )


def _update_pre_commit_hooks():
    try:
        subprocess.run(["pre-commit", "autoupdate"], check=True, capture_output=True)
        click.secho("\tPre-commit hooks updated to latest versions", fg="green")
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.secho(
            "\tNote: Run 'pre-commit autoupdate' to get latest hook versions",
            fg="yellow",
        )


def _print_instructions(project_slug):
    click.echo()
    click.secho("\tNext steps:", fg="yellow")
    click.echo()
    click.secho(f"\t   cd {project_slug}", fg="cyan")
    click.secho("\t   Follow README.md > Development > Setup", fg="cyan")
    click.echo()


def _replace_in_file(file_path, string_to_replace, replacement_string):
    with open(file_path, "r") as file:
        content = file.read()

    updated_content = content.replace(string_to_replace, replacement_string)

    with open(file_path, "w") as file:
        file.write(updated_content)


if __name__ == "__main__":
    main()
