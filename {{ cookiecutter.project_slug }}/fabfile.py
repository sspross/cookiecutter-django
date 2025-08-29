import getpass

from fabric import Connection, task

TARGET_SERVER = "admin@smini.tail9af27c.ts.net"
TARGET_DIR = "~/projects/{{ cookiecutter.project_slug }}"

passphrase = getpass.getpass("Enter SSH key passphrase: ")
connection = Connection(
    TARGET_SERVER,
    forward_agent=True,  # Use my SSH key to e.g. `git pull`
    connect_kwargs={"passphrase": passphrase},
)

# Make sure `docker` is on PATH (brew binaries)
connection.config.run.env = {"PATH": "/usr/local/bin:$PATH"}


@task
def ps(context):
    with connection.cd(TARGET_DIR):
        connection.run("docker ps")


@task
def deploy(context):
    """Deploy the application to the Mac mini server."""
    with connection.cd(TARGET_DIR):
        connection.run("docker compose down")
        connection.run("git pull")
        connection.run("docker compose build")
        connection.run("docker compose up -d")


@task
def migrate(context):
    """Run migrations on the Mac mini server."""
    with connection.cd(TARGET_DIR):
        connection.run("docker compose exec web uv run python manage.py migrate")
