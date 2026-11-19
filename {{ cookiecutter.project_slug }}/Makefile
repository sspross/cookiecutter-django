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

test.live.watch: frontend.build
	@dirs=$$(find . -type d -path '*/tests/live' -not -path '*/.venv/*' -not -path '*/node_modules/*'); \
	if [ -z "$$dirs" ]; then echo "No tests/live directories found"; exit 1; fi; \
	uv run pytest --headed --slowmo 500 -s $$dirs

test.live.record: frontend.build
	@dirs=$$(find . -type d -path '*/tests/live' -not -path '*/.venv/*' -not -path '*/node_modules/*'); \
	if [ -z "$$dirs" ]; then echo "No tests/live directories found"; exit 1; fi; \
	uv run pytest --video on --tracing on --output test-results $$dirs; \
	echo "Artifacts in ./test-results. Drag trace.zip to https://trace.playwright.dev"

# The static checks only import the settings. They get fixed throwaway values, so the
# result is the same with any .env, without one, and in CI. A value set here wins over
# the shell environment and over .env.
lint.types lint.migrations lint.deploy schema: export SECRET_KEY := static-check-secret-key-0123456789abcdefghijklmnopqrstuvwxyz
lint.types lint.migrations lint.deploy schema: export DATABASE_URL := sqlite://:memory:
lint.deploy: export DEBUG := False
lint.deploy: export ALLOWED_HOSTS := example.com
lint.deploy: export HTTPS_ENFORCED := true

lint:
	uv run ruff check .
	uv run tach check
	@$(MAKE) --no-print-directory lint.types
	uv run deptry .
	uv run ast-grep scan
	@$(MAKE) --no-print-directory lint.migrations
	@$(MAKE) --no-print-directory lint.deploy
	cd core/frontend && npm run lint
	cd core/frontend && npm run typecheck

lint.types:
	uv run mypy .

lint.migrations:
	uv run python manage.py makemigrations --check --dry-run

lint.deploy:
	uv run python manage.py check --deploy --tag security --fail-level WARNING

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

up:
	@./scripts/local-stack.sh up

down:
	@./scripts/local-stack.sh down

destroy:
	@./scripts/local-stack.sh destroy

logs:
	@./scripts/local-stack.sh logs

doctor:
	@./scripts/doctor.sh

schema:
	uv run python manage.py export_openapi_schema -o core/frontend/.openapi.json
	cd core/frontend && npm run schema
	rm -f core/frontend/.openapi.json
