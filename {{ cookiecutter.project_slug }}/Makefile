.PHONY: test lint format precommit \
	db.recreate db.initialize db.snapshot db.restore \
	frontend.install frontend.build frontend.lint frontend.dev \
	codegen codegen.check \
	dev.up dev.down dev.django dev.vite

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

precommit:
	uv run pre-commit run --all-files
	uv run pre-commit run --hook-stage manual --all-files

# --- database --------------------------------------------------------
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

# --- frontend --------------------------------------------------------
frontend.install:
	cd frontend && npm install

frontend.build:
	cd frontend && npm run build

frontend.lint:
	cd frontend && npm run lint

frontend.dev:
	cd frontend && npm run dev

# --- codegen ---------------------------------------------------------
# Regenerate the typed API declaration from the live OpenAPI document. No
# running server required — the management command imports the NinjaAPI
# instance directly.
codegen:
	uv run python manage.py dump_openapi --out frontend/openapi.json
	cd frontend && npm run codegen

# Fail if the committed types are stale relative to the current schema.
# Used by CI and by the cookiecutter `make test` to catch backend changes
# that forget a frontend regen.
codegen.check: codegen
	@if ! git diff --quiet -- frontend/types/api.d.ts; then \
		echo "ERROR: generated API types are stale. Run \`make codegen\` and commit the changes."; \
		git --no-pager diff -- frontend/types/api.d.ts; \
		exit 1; \
	fi
	@echo "codegen.check OK"

# --- dev workflow ---------------------------------------------------
# Three predictable commands in three terminals.
dev.up:
	docker compose up -d

dev.down:
	docker compose down

dev.django:
	uv run python manage.py runserver

dev.vite:
	cd frontend && npm run dev
