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

# run_step(command, assert_pattern)
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

# run_step_smoke(command, assert_pattern)
# Runs command for 10s, kills the process tree, then checks output.
# PYTHONUNBUFFERED=1 ensures Python output is flushed to file immediately.
# timeout/gtimeout kills the entire process group (setpgid).
define run_step_smoke
	@printf "  \`$(1)\`"; \
	logfile=$$(mktemp); \
	TIMEOUT_CMD=""; \
	if command -v timeout >/dev/null 2>&1; then \
		TIMEOUT_CMD="timeout"; \
	elif command -v gtimeout >/dev/null 2>&1; then \
		TIMEOUT_CMD="gtimeout"; \
	fi; \
	if [ -n "$$TIMEOUT_CMD" ]; then \
		( cd $(PROJDIR) && NO_COLOR=1 PYTHONUNBUFFERED=1 $$TIMEOUT_CMD 10 $(1) ) > "$$logfile" 2>&1 || true; \
	else \
		( cd $(PROJDIR) && NO_COLOR=1 PYTHONUNBUFFERED=1 $(1) ) > "$$logfile" 2>&1 & \
		PID=$$!; \
		sleep 10; \
		kill_tree() { \
			local children=$$(pgrep -P "$$1" 2>/dev/null); \
			for child in $$children; do \
				kill_tree "$$child"; \
			done; \
			kill -KILL "$$1" 2>/dev/null; \
		}; \
		kill_tree $$PID; \
		wait $$PID 2>/dev/null; \
	fi; \
	output=$$(cat "$$logfile"); \
	rm -f "$$logfile"; \
	if [ -n "$(2)" ] && ! echo "$$output" | grep -q "$(2)"; then \
		echo " FAILED (expected: $(2))"; \
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
	$(call run_step,uv run --with cookiecutter --with django python -m cookiecutter $(CURDIR) --no-input -o "$(TMPDIR)")
	$(call run_step,uv sync,Installed)
	$(call run_step,git init -q && git add --all && uv run pre-commit install,pre-commit installed)
	$(call run_step,uv run playwright install chromium)
	$(call run_step,make db.initialize,Installed 1 object)
	$(call run_step,make frontend.install,added)
	$(call run_step,make frontend.build,built in)
	$(call run_step,uv run python manage.py collectstatic --noinput,static files copied)
	@echo ""
	@echo "2. Verification:"
	@echo ""
	$(call run_step,make test,passed)
	$(call run_step,make lint,All checks passed)
	$(call run_step,make format,left unchanged)
	$(call run_step,make precommit,Passed)
	$(call run_step,uv run pytest api_keys/tests/live,passed)
	$(call run_step_smoke,make frontend.dev,Local:)
	$(call run_step_smoke,uv run python manage.py runserver,Watching for file changes)
	@echo ""
	@rm -rf "$(TMPDIR)"
	@echo "All checks passed!"
