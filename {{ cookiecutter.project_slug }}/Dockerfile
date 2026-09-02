FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# nodejs/npm are needed for the Vite frontend build below.
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    nodejs \
    npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-group dev --group prod

COPY . .

# collectstatic below needs SECRET_KEY/DATABASE_URL to import settings.
COPY .env.example .env

RUN make frontend.install
RUN make frontend.build

RUN uv run python manage.py collectstatic --noinput

# Drop it again so the orchestrator's env vars win at runtime.
RUN rm -f .env
