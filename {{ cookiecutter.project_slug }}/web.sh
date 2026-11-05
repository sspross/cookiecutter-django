#!/bin/bash
set -e
# 5 = 2 * CPUs + 1 on a 2-core box; retune per host.
uv run gunicorn --bind "0.0.0.0:${PORT:-8000}" --timeout 120 --workers 5 core.wsgi --log-file -
