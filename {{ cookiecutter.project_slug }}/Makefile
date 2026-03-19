test:
	@echo "pytest running..."; \
	output=$$(uv run pytest 2>&1); \
	status=$$?; \
	if [ $$status -eq 0 ]; then \
		echo "$$output" | tail -n 1; \
	else \
		echo "$$output"; \
		exit $$status; \
	fi

lint:
	uv run ruff check .
	uv run tach check

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

frontend.install:
	cd core/frontend && npm install

frontend.build:
	cd core/frontend && npm run build

frontend.lint:
	cd core/frontend && npm run lint

frontend.dev:
	cd core/frontend && npm run dev
