#!/bin/bash
set -e
uv run python manage.py rqworker default
