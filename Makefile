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
# Starts a long-running command, waits only until assert_pattern shows up in
# its output (polling every 0.1s, giving up after 15s), then kills the process
# tree. An assert_pattern is required: it is the exit condition, not just an
# assertion. PYTHONUNBUFFERED=1 makes Python flush to the file immediately.
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

TMPDIR := $(shell mktemp -d)
PROJDIR := $(TMPDIR)/django-website

test:
	@echo "Testing cookiecutter template."
	@echo "1. Setup:"
	@echo ""
	$(call run_step,uv run --with cookiecutter --with django python -m cookiecutter $(CURDIR) --no-input -o "$(TMPDIR)")
	$(call run_step,uv sync,Installed)
	$(call run_step,make frontend.install,added)
	$(call run_step,git init -q && git add --all && uv run pre-commit install,pre-commit installed)
	$(call run_step,git ls-files --error-unmatch uv.lock core/frontend/package-lock.json,package-lock.json)
	$(call run_step,uv run playwright install chromium)
	$(call run_step,make db.initialize,Installed 1 object)
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
	@echo ""
	@rm -rf "$(TMPDIR)"
	@echo "All checks passed!"
