test: frontend.build
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

backend.dev:
	uv run python manage.py runserver

# Local worker uses SimpleWorker (in-process, no os.fork() — fork-safe on
# macOS). Prod (worker.sh) uses the forking `rqworker`. Write jobs correct
# under BOTH: don't rely on in-process state surviving between jobs, and
# don't rely on SimpleWorker's lack of a hard per-job timeout — prod enforces
# RQ_QUEUES DEFAULT_TIMEOUT and kills the job. See docs/adr/0003.
worker.dev:
	uv run python manage.py rqworker default --worker-class rq.worker.SimpleWorker

dev: # one-command dev loop: tmux with a shell + frontend/backend/worker panes
	./scripts/dev.sh

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
