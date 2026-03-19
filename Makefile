test:
	@echo "Testing cookiecutter template..."; \
	TMPDIR=$$(mktemp -d); \
	echo "Generating project in $$TMPDIR..."; \
	uv run --with cookiecutter --with django python -m cookiecutter . --no-input -o "$$TMPDIR" && \
	cd "$$TMPDIR/django-website" && \
	echo "Installing dependencies..." && \
	uv sync && \
	echo "Installing frontend..." && \
	make frontend.install && \
	make frontend.build && \
	echo "Running migrations..." && \
	DATABASE_URL=sqlite:///db.sqlite3 SECRET_KEY=test-secret-key \
		uv run python manage.py migrate && \
	echo "Collecting static files..." && \
	DATABASE_URL=sqlite:///db.sqlite3 SECRET_KEY=test-secret-key \
		uv run python manage.py collectstatic --noinput && \
	echo "Running tests..." && \
	DATABASE_URL=sqlite:///db.sqlite3 SECRET_KEY=test-secret-key \
		uv run pytest -v -m "not browser" && \
	echo "Running lint..." && \
	make lint && \
	echo "Cleaning up..." && \
	rm -rf "$$TMPDIR" && \
	echo "Template test passed!"
