#!/bin/bash
set -e
#
# Workers are separate UNIX processes, each loading the application, so memory
# scales with the count. 5 = 2 * CPUs + 1 on a 2-core box; retune per host.
#
uv run gunicorn --timeout 120 --workers 5 core.wsgi --log-file -
