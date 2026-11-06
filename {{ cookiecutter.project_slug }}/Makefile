test: frontend.build
	@echo "pytest running..."; \
	output=$$(uv run pytest -n 4 2>&1); \
	status=$$?; \
	if [ $$status -eq 0 ]; then \
		echo "$$output" | tail -n 1; \
	else \
		echo "$$output"; \
		exit $$status; \
	fi

test.coverage: frontend.build
	uv run pytest -n 4 --cov --cov-report=term

test.live.watch: frontend.build
	@dirs=$$(find . -type d -path '*/tests/live' -not -path '*/.venv/*' -not -path '*/node_modules/*'); \
	if [ -z "$$dirs" ]; then echo "No tests/live directories found"; exit 1; fi; \
	uv run pytest --headed --slowmo 500 -s $$dirs

test.live.record: frontend.build
	@dirs=$$(find . -type d -path '*/tests/live' -not -path '*/.venv/*' -not -path '*/node_modules/*'); \
	if [ -z "$$dirs" ]; then echo "No tests/live directories found"; exit 1; fi; \
	uv run pytest --video on --tracing on --output test-results $$dirs; \
	echo "Artifacts in ./test-results — drag trace.zip to https://trace.playwright.dev"

lint:
	uv run ruff check .
	uv run tach check
	uv run mypy .
	uv run deptry .
	uv run python manage.py makemigrations --check --dry-run
	DEBUG=False ALLOWED_HOSTS=example.com SECRET_KEY=deploy-check-secret-key-0123456789abcdefghijklmnopqrstuvwxyz uv run python manage.py check --deploy --tag security --fail-level WARNING
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

frontend.install.ci:
	cd core/frontend && npm ci

frontend.build:
	cd core/frontend && npm run build

frontend.dev:
	cd core/frontend && npm run dev

backend.dev:
	uv run python manage.py runserver

# SimpleWorker avoids os.fork(), which is unsafe on macOS, see docs/adr/0003-async-by-default.md.
worker.dev:
	uv run python manage.py rqworker default --worker-class rq.worker.SimpleWorker

dev:
	./scripts/dev.sh

schema:
	uv run python manage.py export_openapi_schema -o core/frontend/.openapi.json
	cd core/frontend && npm run schema
	rm -f core/frontend/.openapi.json

db.recreate:
	dropdb --if-exists --force {{ cookiecutter.project_slug }}
	createdb {{ cookiecutter.project_slug }}

db.migrate:
	uv run python manage.py migrate

db.snapshot:
	dropdb --if-exists {{ cookiecutter.project_slug }}_snapshot
	createdb -O postgres -T {{ cookiecutter.project_slug }} {{ cookiecutter.project_slug }}_snapshot

db.restore:
	dropdb --if-exists {{ cookiecutter.project_slug }}
	createdb -O postgres -T {{ cookiecutter.project_slug }}_snapshot {{ cookiecutter.project_slug }}
