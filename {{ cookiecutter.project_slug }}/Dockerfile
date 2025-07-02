# For appliku.com usage only. For more details about why /code/ and /env/ see
# https://appliku.com/post/using-custom-dockerfile-appliku

# ----------------------------------------------------------------------------
# Django app with uv package manager - Multi-stage build
# ----------------------------------------------------------------------------

# Stage 1: Builder
FROM python:3.12-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.10 /uv /usr/local/bin/uv

# Set up working directory
WORKDIR /code/

# Set environment for uv to create proper virtual environment
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy dependency files first (better caching)
COPY /code/pyproject.toml /code/pyproject.toml
COPY /code/uv.lock /code/uv.lock

# Create virtual environment and install dependencies
RUN uv venv .venv && \
    uv sync --frozen --no-dev

# Copy source code
COPY /code/ /code/

# ----------------------------------------------------------------------------
# Stage 2: Runtime
FROM python:3.12-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user early
RUN useradd -ms /bin/bash code

# Set up working directory
WORKDIR /code/

# Copy virtual environment from builder (with correct ownership)
COPY --from=builder --chown=code:code /code/.venv /code/.venv

# Copy source code from builder (with correct ownership)
COPY --from=builder --chown=code:code /code /code/

# Copy env directory (required by Appliku)
COPY /env/ /env/

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PATH="/code/.venv/bin:$PATH" \
    VIRTUAL_ENV="/code/.venv"

# MUST have an .env file
RUN touch /code/.env && chown code:code /code/.env

# Fix permissions for /env directory
RUN chown -R code:code /env || true

# Switch to non-root user
USER code

# Fix dubious ownership in repository warning
RUN git config --global --add safe.directory /code

# Collect static files (using virtual environment)
RUN --mount=type=bind,source=/env/envs_export.sh,target=/env/envs_export.sh \
    bash -c "source /env/envs_export.sh && cd /code/ && python manage.py collectstatic --noinput"

# Default command (using virtual environment's gunicorn)
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]