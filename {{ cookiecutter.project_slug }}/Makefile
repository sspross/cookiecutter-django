test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

db.recreate:
	dropdb --if-exists --force {{ cookiecutter.project_slug }}
	createdb {{ cookiecutter.project_slug }}

db.initialize:
	uv run python manage.py migrate
	uv run python manage.py loaddata dumpdata.json

db.snapshot:
	dropdb --if-exists {{ cookiecutter.project_slug }}_snapshot
	createdb -O postgres -T {{ cookiecutter.project_slug }} {{ cookiecutter.project_slug }}_snapshot

db.restore:
	dropdb --if-exists {{ cookiecutter.project_slug }}
	createdb -O postgres -T {{ cookiecutter.project_slug }}_snapshot {{ cookiecutter.project_slug }}
