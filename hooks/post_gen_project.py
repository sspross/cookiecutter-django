import random
import string
import shutil
import click


def main():
    # Do some important stuff after copying the project template.
    # 1. Create env file with fresh secret key
    shutil.copyfile(".env.example", ".env")
    _set_django_secret_key(".env")

    # 2. Print further instructions
    click.echo()
    click.secho("\tNext steps:", fg="yellow")
    click.echo()
    click.secho("\t1. Navigate to your project directory:", fg="blue")
    click.secho("\t   cd {{cookiecutter.project_slug}}", fg="cyan")
    click.echo()
    click.secho("\t2. Put project under version control", fg="blue")
    click.secho("\t   git init", fg="cyan")
    click.secho("\t   git add --all", fg="cyan")
    click.secho('\t   git commit -m "Initial setup from django project template"', fg="cyan")
    click.echo()
    click.secho("\t3. Open VS Code and follow instructions in project README:", fg="blue")
    click.secho("\t   code .", fg="cyan")
    click.echo()


def _set_django_secret_key(env_file):
    secret_key = "".join(
        random.SystemRandom().choice(
            string.ascii_letters + string.digits
        )
        for _ in range(50)
    )
    with open(env_file, "r") as f:
        lines = f.readlines()
    with open(env_file, "w") as f:
        for line in lines:
            if line.startswith("SECRET_KEY="):
                f.write(f"SECRET_KEY={secret_key}\n")
            else:
                f.write(line)


if __name__ == "__main__":
    main()
