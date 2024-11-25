#!/bin/bash
set -e
poetry run ./manage.py migrate
