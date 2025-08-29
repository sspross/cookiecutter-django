import click  # dependency of cookiecutter
import random
import shutil
import string

from django.conf import settings
from django.contrib.auth.hashers import make_password


ENV_EXAMPLE_FILE = ".env.example"
ENV_FILE = ".env"
DUMPDATA_FILE = "dumpdata.json"


def main():
    django_password = "{{ cookiecutter.django_password }}"
    project_slug = "{{ cookiecutter.project_slug }}"
    secret_key = _create_django_secret_key()

    # 1. Create env file with fresh secret key
    shutil.copyfile(ENV_EXAMPLE_FILE, ENV_FILE)
    _replace_in_file(ENV_FILE, "replace-with-secret-key", secret_key)

    # 2. Create a password hash for the default admin user
    password = _create_django_password(django_password, secret_key)
    _replace_in_file(DUMPDATA_FILE, "replace-with-password-hash", password)

    # 2. Print further instructions
    _print_instructions(project_slug)


def _create_django_secret_key():
    return "".join(
        random.SystemRandom().choice(string.ascii_letters + string.digits)
        for _ in range(50)
    )


def _create_django_password(password, secret_key):
    settings.configure(
        PASSWORD_HASHERS=[
            "django.contrib.auth.hashers.PBKDF2PasswordHasher",
        ]
    )
    return make_password(password, salt=secret_key)


def _print_instructions(project_slug):
    click.echo()
    click.secho("\tNext steps:", fg="yellow")
    click.echo()
    click.secho("\t1. Navigate to your project directory:", fg="blue")
    click.secho(f"\t   cd {project_slug}", fg="cyan")
    click.echo()
    click.secho("\t2. Put project under version control", fg="blue")
    click.secho("\t   git init", fg="cyan")
    click.secho("\t   git add --all", fg="cyan")
    click.secho(
        '\t   git commit -m "Initial setup from django project template"', fg="cyan"
    )
    click.echo()
    click.secho("\t3. Follow instructions in project README:", fg="blue")
    click.secho("\t   code .", fg="cyan")
    click.echo()


def _replace_in_file(file_path, string_to_replace, replacement_string):
    with open(file_path, "r") as file:
        content = file.read()

    updated_content = content.replace(string_to_replace, replacement_string)

    with open(file_path, "w") as file:
        file.write(updated_content)


if __name__ == "__main__":
    main()
