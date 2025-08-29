FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

# Install system dependencies including Node.js for Tailwind
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    nodejs \
    npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies including prod group
RUN uv sync --frozen --no-group dev --group prod

# Copy project code
COPY . .

# Copy .env file if it exists
COPY .env.example .env

# Install Javascript and CSS dependencies
RUN make frontend.install
RUN make frontend.build

# Collect static files
RUN uv run python manage.py collectstatic --noinput

# Remove .env file to use docker-compose env variables
RUN rm -f .env

# Run the application
EXPOSE 8000
CMD ["uv", "run", "gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]