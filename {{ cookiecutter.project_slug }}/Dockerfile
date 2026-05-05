# Multi-stage build with two named targets:
#
#   builder — installs Python + Node deps, builds the SPA, runs collectstatic
#   app     — minimal Python runtime that runs gunicorn (the single deploy
#             artifact used by both compose-on-VM and Appliku)

ARG PYTHON_VERSION=3.13-slim
ARG NODE_VERSION=22-bookworm-slim

# ------- builder ----------------------------------------------------
FROM python:${PYTHON_VERSION} AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-group dev --group prod

COPY . .
COPY .env.example .env

RUN make frontend.install \
    && make frontend.build \
    && uv run python manage.py collectstatic --noinput \
    && rm -f .env

# ------- app --------------------------------------------------------
FROM python:${PYTHON_VERSION} AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY --from=builder /app /app

EXPOSE 8000
CMD ["uv", "run", "gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
