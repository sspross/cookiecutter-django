#!/bin/bash
set -e
#
# The forking worker (prod). Scale by running more of these; each is its own
# UNIX process with no shared memory. Local dev uses `make worker.dev`
# (SimpleWorker). See ADR-0003.
#
uv run python manage.py rqworker default
