# For appliku.com usage only. For more details about why /code/ and /env/ see
# https://appliku.com/post/using-custom-dockerfile-appliku

# ----------------------------------------------------------------------------
# Django app with uv package manager
# ----------------------------------------------------------------------------
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.10 /uv /usr/local/bin/uv

# Set up working directory
WORKDIR /code/

# Allow statements and log messages to immediately appear in the container logs
ENV PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1

# Copy dependency files
COPY /code/pyproject.toml /code/
COPY /code/uv.lock /code/

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY /code/ /code/
COPY /env/ /env/

# MUST have an .env file
RUN touch /code/.env

# Collect static files
RUN --mount=type=bind,source=/env/envs_export.sh,target=/env/envs_export.sh \
    bash -c "source /env/envs_export.sh && cd /code/ && uv run python manage.py collectstatic --noinput"

# Create non-root user
RUN useradd -ms /bin/bash code && \
    chown -R code:code /code

USER code

# Fix dubious ownership in repository warning
RUN git config --global --add safe.directory /code
