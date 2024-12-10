#!/bin/bash
set -e
poetry run ./manage.py migrate
poetry run ./manage.py loaddata dumpdata.json
