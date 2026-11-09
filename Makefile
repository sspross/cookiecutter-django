define show_tail
	trimmed=$$(echo "$$output" | sed '/^[[:space:]]*$$/d'); \
	if [ -n "$$trimmed" ]; then \
		total=$$(echo "$$trimmed" | wc -l | tr -d ' '); \
		printf "\033[90m"; \
		echo "  ┌──"; \
		if [ "$$total" -gt 5 ]; then \
			echo "  │ ..."; \
		fi; \
		echo "$$trimmed" | tail -n 5 | while IFS= read -r line; do \
			echo "  │ $$line"; \
		done; \
		echo "  └──"; \
		printf "\033[0m"; \
	fi
endef

define run_step
	@printf "  \`$(1)\`"; \
	output=$$(cd $(PROJDIR) 2>/dev/null; $(1) 2>&1); \
	status=$$?; \
	if [ $$status -ne 0 ]; then \
		echo " FAILED (exit $$status)"; \
		echo "$$output"; \
		exit $$status; \
	fi; \
	if [ -n "$(2)" ] && ! echo "$$output" | grep -q "$(2)"; then \
		echo " FAILED (expected: $(2))"; \
		echo "$$output"; \
		exit 1; \
	fi; \
	echo ""; \
	$(show_tail)
endef

# $(2) is required: it is the exit condition, and an empty one kills the command
# at its first output line and passes.
define run_step_smoke
	@printf "  \`$(1)\`"; \
	logfile=$$(mktemp); \
	( cd $(PROJDIR) && NO_COLOR=1 PYTHONUNBUFFERED=1 $(1) ) > "$$logfile" 2>&1 & \
	pid=$$!; \
	for i in $$(seq 1 150); do \
		if grep -q "$(2)" "$$logfile" 2>/dev/null; then break; fi; \
		if ! kill -0 $$pid 2>/dev/null; then break; fi; \
		sleep 0.1; \
	done; \
	kill_tree() { \
		for child in $$(pgrep -P "$$1" 2>/dev/null); do \
			kill_tree "$$child"; \
		done; \
		kill -KILL "$$1" 2>/dev/null; \
	}; \
	kill_tree $$pid; \
	wait $$pid 2>/dev/null; \
	output=$$(cat "$$logfile"); \
	rm -f "$$logfile"; \
	if ! echo "$$output" | grep -q "$(2)"; then \
		echo " FAILED (expected: $(2))"; \
		echo "$$output"; \
		exit 1; \
	fi; \
	echo ""; \
	$(show_tail)
endef

# $(1) is the check, $(2) what it must print, $(3) the file to plant in, $(4) the planted
# code (\n for a newline, no commas or single quotes).
define run_canary
	@printf "  \`$(1)\` catches $(2)"; \
	cd $(PROJDIR); \
	cp "$(3)" "$(3).canary"; \
	printf '%b\n' '\n$(4)' >> "$(3)"; \
	output=$$($(1) 2>&1); \
	status=$$?; \
	mv "$(3).canary" "$(3)"; \
	if [ $$status -eq 0 ] || ! echo "$$output" | grep -q "$(2)"; then \
		echo " FAILED (canary did not fire: $(2))"; \
		echo "$$output"; \
		exit 1; \
	fi; \
	echo ""; \
	$(show_tail)
endef

TMPDIR := $(shell mktemp -d)
PROJDIR := $(TMPDIR)/django-website

test:
	@echo "Testing cookiecutter template."
	@echo "1. Setup:"
	@echo ""
	$(call run_step,cd $(dir $(CURDIR)) && uv run --with cookiecutter python -m cookiecutter $(notdir $(CURDIR)) --no-input -o "$(TMPDIR)")
	$(call run_step,uv sync,Installed)
	$(call run_step,make frontend.install,added)
	$(call run_step,git init -q && git add --all && uv run pre-commit install,pre-commit installed)
	$(call run_step,git ls-files --error-unmatch uv.lock core/frontend/package-lock.json,package-lock.json)
	$(call run_step,git ls-files --error-unmatch .template.json,.template.json)
	$(call run_step,uv run playwright install chromium)
	$(call run_step,make db.migrate,Applying)
	$(call run_step,make lint,All checks passed)
	$(call run_step,make frontend.build,built in)
	$(call run_step,uv run python manage.py collectstatic --noinput,static files copied)
	@echo ""
	@echo "2. Verification:"
	@echo ""
	$(call run_step,make test,passed)
	$(call run_step,make lint,All checks passed)
	$(call run_step,make format,left unchanged)
	$(call run_step,make precommit,Passed)
	$(call run_step_smoke,make frontend.dev,Local:)
	$(call run_step_smoke,uv run python manage.py runserver,Starting WSGI development server)
	$(call run_step,bash $(CURDIR)/tests/local_stack_smoke.sh,make up took 8001)
	@echo ""
	@echo "3. Canaries:"
	@echo ""
	$(call run_canary,uv run ruff check .,TID251.*ADR-0007,core/urls.py,import sentry_sdk\nsentry_sdk.capture_exception())
	$(call run_canary,uv run ruff check .,PLC0415,core/urls.py,def canary() -> None:\n    import json)
	$(call run_canary,uv run ruff check .,TD003,core/urls.py,# TODO: canary)
	$(call run_canary,uv run tach check,not part of the public interface,core/urls.py,from api_keys.models import UserApiKey\nUserApiKey)
	$(call run_canary,uv run mypy .,no-untyped-def,core/urls.py,def canary():\n    return 1)
	$(call run_canary,make lint,Create model Canary,users/models.py,from django.db import models  # noqa: E402\n\n\nclass Canary(models.Model):\n    name = models.CharField(max_length=10)\n\n    def __str__(self) -> str:\n        return self.name)
	$(call run_canary,uv run pytest core/tests/test_healthz.py -k canary,UserWarning: canary,core/tests/test_healthz.py,import warnings\n\n\ndef test_canary() -> None:\n    warnings.warn("canary"))
	$(call run_step,make lint,All checks passed)
	@echo ""
	@rm -rf "$(TMPDIR)"
	@echo "All checks passed!"
