#!/bin/bash
set -e
#
# RQ WORKER
# --
# Processes background jobs from the "default" Redis queue. Run alongside
# `web.sh` so the web process stays free for HTTP traffic and the worker
# handles long-running jobs.
#
# Scale by running multiple `worker.sh` processes. Each worker is its own
# UNIX process loading the Python application; there is no shared memory
# between workers.
#
uv run python manage.py rqworker default
