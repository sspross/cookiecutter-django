#!/bin/bash
set -e
uv run ./manage.py migrate
uv run ./manage.py loaddata dumpdata.json
