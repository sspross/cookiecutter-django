# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a cookiecutter template for Django projects. It generates modern, production-ready Django applications with best practices and contemporary tooling.

## Common Development Commands

### Project Setup
```bash
# Generate a new project from this template
cookiecutter git@github.com:sspross/cookiecutter_django.git

# In the generated project:
cd [project-slug]
uv sync                          # Install dependencies
make db.recreate                 # Create database
make db.initialize               # Run migrations and load initial data
uv run python manage.py runserver # Start development server
```

### Daily Development
```bash
# Run tests
make test

# Lint code
make lint

# Format code
make format

# Run development server
uv run python manage.py runserver

# Create migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate

# Create superuser
uv run python manage.py createsuperuser

# Django shell
uv run python manage.py shell
```

### Database Management
```bash
make db.recreate    # Drop and recreate database
make db.initialize  # Run migrations and load initial data
make db.snapshot    # Create database backup
make db.restore     # Restore from backup
```

## Architecture & Key Patterns

### Template Structure
The cookiecutter template has two main directories:
- `{{ cookiecutter.project_slug }}/` - The actual Django project template files
- Root level files - Cookiecutter configuration and documentation

### Generated Project Structure
Projects created from this template follow this structure:
- `core/` - Main Django app containing all initial functionality
- Single app pattern - Start with one app and grow as needed
- Mixed templating - Both Jinja2 (preferred) and Django templates supported
- Environment-based configuration using django-environ
- WhiteNoise for static file serving with compression
- Gunicorn for production WSGI server

### Key Technical Decisions
- **Package Management**: Uses `uv` (not poetry or pip)
- **Database**: PostgreSQL required
- **Static Files**: WhiteNoise with ManifestStaticFilesStorage
- **Media Files**: Configured for direct serving in development
- **Deployment**: Optimized for Appliku.com platform
- **Initial Data**: Includes admin user in dumpdata.json

### Configuration Pattern
All sensitive settings use environment variables via django-environ:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Django secret key
- `DEBUG` - Debug mode flag
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts

### Development Workflow
1. Always use `uv` for dependency management
2. Run tests before committing: `make test`
3. Keep code formatted: `make format`
4. The Makefile contains all common operations
5. Initial admin credentials are in dumpdata.json (password gets hashed during setup)

### Post-Generation Hook
The `post_gen_project.py` script runs after project generation to:
- Generate a secure SECRET_KEY
- Create .env file from .env.example
- Hash the admin password in dumpdata.json
- Display setup instructions

### Important Files to Understand
- `{{ cookiecutter.project_slug }}/core/settings.py` - Django configuration with environment variables
- `{{ cookiecutter.project_slug }}/Makefile` - All development commands
- `{{ cookiecutter.project_slug }}/pyproject.toml` - Project dependencies and tool configuration
- `post_gen_project.py` - Runs after cookiecutter generates the project
- `cookiecutter.json` - Template variables and defaults