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

test.live.watch: frontend.build # run live (Playwright) tests with a visible, slowed-down browser
	@dirs=$$(find . -type d -path '*/tests/live' -not -path '*/.venv/*' -not -path '*/node_modules/*'); \
	if [ -z "$$dirs" ]; then echo "No tests/live directories found"; exit 1; fi; \
	HEADED=1 SLOWMO_MS=500 uv run pytest -s $$dirs

lint:
	uv run ruff check .
	uv run tach check
	cd core/frontend && npm run lint
	cd core/frontend && npm run typecheck

format:
	uv run ruff format .
	cd core/frontend && npm run lint:fix

precommit:
	uv run pre-commit run --all-files
	uv run pre-commit run --hook-stage manual --all-files

frontend.install:
	cd core/frontend && npm install

frontend.build:
	cd core/frontend && npm run build

frontend.dev:
	cd core/frontend && npm run dev

schema:
	cd core/frontend && npm run schema

db.recreate: # only work with local Postgres, not SQLite
	dropdb --if-exists --force {{ cookiecutter.project_slug }}
	createdb {{ cookiecutter.project_slug }}

db.initialize:
	uv run python manage.py migrate
	uv run python manage.py loaddata dumpdata.json

db.snapshot: # only work with local Postgres, not SQLite
	dropdb --if-exists {{ cookiecutter.project_slug }}_snapshot
	createdb -O postgres -T {{ cookiecutter.project_slug }} {{ cookiecutter.project_slug }}_snapshot

db.restore: # only work with local Postgres, not SQLite
	dropdb --if-exists {{ cookiecutter.project_slug }}
	createdb -O postgres -T {{ cookiecutter.project_slug }}_snapshot {{ cookiecutter.project_slug }}
