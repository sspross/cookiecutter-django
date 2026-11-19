#!/bin/bash
set -e
exec python manage.py rqworker default
