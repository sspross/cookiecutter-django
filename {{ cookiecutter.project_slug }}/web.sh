#!/bin/bash
set -e
#
# WORKERS (2 * number of CPUs + 1)
# --
# Each of the workers is a UNIX process that loads the Python application.
# There is no shared memory between the workers. So n times the memory.
#
#  gunicorn --workers=5 core.wsgi --log-file -
#
# THREADS
# --
# Each of the workers can have multiple threads. The Python application is
# loaded once per worker, and each of the threads spawned by the same worker
# shares the same memory space.
#
#   gunicorn --workers=2 --threads=2 --worker-class=gthread core.wsgi --log-file -
#
# The maximum concurrent requests are WORKERS * THREADS and the suggested
# maximum concurrent requests when using workers and threads is still 2 *
# number of CPUs + 1. If you don’t know you are doing, start with the simplest
# configuration, which is only setting workers to 2 * number of CPUs + 1 and
# don’t worry about threads. From that point, it’s all trial and error with
# benchmarking:
#
# - If the bottleneck is memory, start introducing threads.
# - If the bottleneck is I/O, consider a different python programming paradigm.
# - If the bottleneck is CPU, consider using more cores and adjusting the workers value.
#
uv run gunicorn --timeout 120 --workers 5 core.wsgi --log-file -
