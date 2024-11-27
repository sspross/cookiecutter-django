db.recreate:
	dropdb --if-exists --force {{ cookiecutter.project_slug }}
	createdb {{ cookiecutter.project_slug }}

db.snapshot:
	dropdb --if-exists {{ cookiecutter.project_slug }}_snapshot
	createdb -O postgres -T {{ cookiecutter.project_slug }} {{ cookiecutter.project_slug }}_snapshot

db.restore:
	dropdb --if-exists {{ cookiecutter.project_slug }}
	createdb -O postgres -T {{ cookiecutter.project_slug }}_snapshot {{ cookiecutter.project_slug }}
