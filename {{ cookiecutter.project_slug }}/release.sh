#!/bin/bash
set -e
uv run ./manage.py migrate
