FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# Debian package versions change with the base image, so apt pins would break the build.
# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    nodejs \
    npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid app --home-dir /app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-group dev --group prod

COPY . .

# collectstatic below needs SECRET_KEY/DATABASE_URL to import settings.
COPY .env.example .env

RUN make frontend.install.ci
RUN make frontend.build

RUN uv run python manage.py collectstatic --noinput

# Never a runtime fallback: .env.example sets DEBUG=True and a placeholder SECRET_KEY.
RUN rm -f .env

RUN chown -R app:app /app

USER app

CMD ["./web.sh"]
