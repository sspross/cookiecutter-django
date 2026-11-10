#!/bin/bash
set -e
exec uv run python manage.py rqworker default
