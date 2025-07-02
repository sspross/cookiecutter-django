# 02_PLAN.md - Cookiecutter Django Template Implementation Plan

## Overview

This document provides a detailed, step-by-step implementation plan for upgrading the cookiecutter-django template according to the specifications in 01_SPEC.md. Each step is designed to be small, safe, and build incrementally on previous steps.

## Implementation Phases

### Phase 0: Foundation Cleanup (Prerequisites)
Small, focused changes to prepare the codebase for larger improvements.

#### Step 0.1: Update .gitignore
- Add comprehensive Python patterns
- Include IDE files, OS-specific files, test artifacts
- Essential for clean repository state

#### Step 0.2: Fix Dockerfile for uv
- Replace pip/poetry references with uv
- Update the multi-stage build process
- Ensure proper caching

#### Step 0.3: Clean up pyproject.toml
- Remove django-jinja dependency
- Ensure all dependencies are properly formatted
- Add any missing development tools

### Phase 1: Template System Migration
Migrate from Jinja2 to Django templates exclusively.

#### Step 1.1: Update Template Configuration
- Modify settings.py TEMPLATES configuration
- Remove Jinja2 backend, keep only Django backend
- Update template directories

#### Step 1.2: Convert Template Files
- Rename .jinja files to .html
- Convert Jinja2 syntax to Django template syntax
- Update template inheritance and includes

#### Step 1.3: Update Views and URLs
- Ensure all views reference .html templates
- Test that template rendering works correctly
- Update any template-related utilities

### Phase 2: Testing Infrastructure
Build a comprehensive testing foundation.

#### Step 2.1: Create Test Directory Structure
- Create tests/ directory with proper structure
- Add __init__.py files
- Create subdirectories for different test types

#### Step 2.2: Add Test Configuration
- Create conftest.py with pytest fixtures
- Add test settings if needed
- Configure test database

#### Step 2.3: Create Test Factories
- Add factory-boy factories for User model
- Create base factory classes
- Add example factories for common patterns

#### Step 2.4: Write Example Tests
- Add model tests
- Add view tests
- Add form tests (if applicable)
- Add integration tests

#### Step 2.5: Add Coverage Configuration
- Configure pytest-cov in pyproject.toml
- Add .coveragerc for coverage settings
- Update Makefile with coverage commands

### Phase 3: Code Quality Tools
Implement automated code quality enforcement.

#### Step 3.1: Create Pre-commit Configuration
- Add .pre-commit-config.yaml
- Configure ruff for linting and formatting
- Add file checking hooks

#### Step 3.2: Add Additional Pre-commit Hooks
- Add pytest hook for failing tests
- Configure YAML/JSON validators
- Add security checks

#### Step 3.3: Update Development Workflow
- Document pre-commit installation in README
- Add Makefile commands for pre-commit
- Test all hooks work correctly

### Phase 4: Security Enhancements
Implement security best practices.

#### Step 4.1: Add Security Middleware
- Configure security middleware in settings
- Add SECURE_* settings
- Test middleware is active

#### Step 4.2: Configure Security Headers
- Add HSTS configuration
- Configure CSP headers
- Add X-Frame-Options and other headers

#### Step 4.3: Secure Cookie Settings
- Configure SESSION_COOKIE_SECURE
- Add CSRF_COOKIE_SECURE
- Configure cookie settings for production

#### Step 4.4: Add CORS Configuration
- Install django-cors-headers
- Configure CORS settings
- Add environment-based CORS configuration

### Phase 5: Django Ninja API
Add modern API capabilities.

#### Step 5.1: Create API App Structure
- Create api/ app directory
- Add version structure (v1/)
- Create endpoints and schemas directories

#### Step 5.2: Configure Django Ninja
- Add django-ninja to dependencies
- Create base API configuration
- Wire up API URLs

#### Step 5.3: Create Example Endpoints
- Add health check endpoint
- Create example CRUD endpoints
- Add authentication examples

#### Step 5.4: Add API Documentation
- Configure OpenAPI/Swagger
- Add API versioning
- Create API documentation

### Phase 6: Settings Refactoring
Modernize settings organization.

#### Step 6.1: Create Settings Package
- Convert settings.py to settings package
- Create base.py with common settings
- Add development.py and production.py

#### Step 6.2: Environment Validation
- Add environment variable validation
- Create custom validators
- Add helpful error messages

#### Step 6.3: Logging Configuration
- Add comprehensive logging setup
- Configure different log levels
- Add structured logging support

### Phase 7: Enhanced Developer Experience
Improve development workflow.

#### Step 7.1: Enhance Makefile
- Add more development commands
- Include test shortcuts
- Add database helpers

#### Step 7.2: Add ABOUTME Comments
- Add descriptive comments to all Python files
- Follow the ABOUTME: pattern
- Document file purposes

#### Step 7.3: Create Comprehensive Documentation
- Write detailed README
- Add architecture documentation
- Create development guide

### Phase 8: CI/CD Setup
Automate quality checks.

#### Step 8.1: Create GitHub Actions Workflow
- Add basic CI workflow
- Configure test running
- Add linting checks

#### Step 8.2: Add Advanced CI Features
- Add security scanning
- Configure dependency updates
- Add deployment workflows

### Phase 9: Advanced Features (Optional)
Nice-to-have improvements.

#### Step 9.1: Debug Toolbar Configuration
- Configure django-debug-toolbar
- Add development-only middleware
- Document usage

#### Step 9.2: Performance Optimizations
- Add caching examples
- Include database optimization tips
- Add async view examples

## Implementation Prompts

Below are the detailed prompts for implementing each step. Each prompt is self-contained but builds on previous steps.

### Step 0.1: Update .gitignore

```text
Update the .gitignore file in the {{ cookiecutter.project_slug }} directory to include comprehensive Python patterns, IDE files, OS-specific files, and test artifacts. The current .gitignore only has basic entries. Please create a comprehensive .gitignore that includes:

1. Python artifacts (__pycache__, *.pyc, *.pyo, etc.)
2. Virtual environment directories (.venv, venv/, env/)
3. IDE files (.idea/, .vscode/, *.swp, *.swo)
4. OS files (.DS_Store, Thumbs.db)
5. Test and coverage artifacts (.coverage, htmlcov/, .pytest_cache/)
6. Environment files (.env, .env.*)
7. Database files (*.sqlite3, *.db)
8. Static and media directories
9. Build artifacts (dist/, build/, *.egg-info/)

Make sure to keep any existing project-specific patterns.
```

### Step 0.2: Fix Dockerfile for uv

```text
Update the Dockerfile in the {{ cookiecutter.project_slug }} directory to use uv instead of pip. The current Dockerfile uses pip for package installation. Please:

1. Update the base image if needed
2. Install uv in the builder stage
3. Copy pyproject.toml and uv.lock files
4. Use 'uv sync' for dependency installation
5. Ensure proper caching for faster builds
6. Update the final stage to copy the virtual environment correctly
7. Update the CMD to use uv run if needed

The Dockerfile should follow Docker best practices and use multi-stage builds efficiently.
```

### Step 0.3: Clean up pyproject.toml

```text
Update the pyproject.toml file in the {{ cookiecutter.project_slug }} directory to:

1. Remove the django-jinja dependency (we're switching to Django templates only)
2. Ensure all dependencies are properly organized in sections
3. Add any missing tool configurations (ruff, pytest, coverage)
4. Ensure the file follows best practices for Python packaging
5. Keep all other existing dependencies

Make sure the file is properly formatted and all versions are specified correctly.
```

### Step 1.1: Update Template Configuration

```text
Update the settings.py file in the {{ cookiecutter.project_slug }}/core directory to remove Jinja2 template configuration and use only Django templates. Currently, the TEMPLATES setting has both Jinja2 and Django backends configured. Please:

1. Remove the Jinja2 backend configuration
2. Keep only the Django template backend
3. Update the DIRS to point to the correct template directories
4. Ensure APP_DIRS is True for the Django backend
5. Keep any context processors that are needed

Make sure the configuration is clean and follows Django best practices.
```

### Step 1.2: Convert Template Files

```text
Convert all Jinja2 templates to Django templates in the {{ cookiecutter.project_slug }} directory. Currently there are .jinja files that need to be converted. Please:

1. Rename all .jinja files to .html
2. Convert Jinja2 syntax to Django template syntax:
   - Change {{ variable }} to {{ variable }} (same)
   - Change {% set var = value %} to {% with var=value %}
   - Change {% endset %} to {% endwith %}
   - Update any Jinja2-specific filters to Django equivalents
   - Change {%- and -%} to regular {% and %}
3. Update template inheritance (extends) and includes
4. Ensure static files are loaded with {% load static %}
5. Update any custom template tags if present

Pay special attention to base.jinja as it has HTMX and Bootstrap setup that needs to be preserved.
```

### Step 1.3: Update Views and URLs

```text
Update all views in the {{ cookiecutter.project_slug }}/core directory to reference the new .html templates instead of .jinja templates. Please:

1. Update all render() calls to use .html extensions
2. Check if there are any template_name attributes that need updating
3. Verify URL patterns still work correctly
4. Ensure no Jinja2-specific code remains in views

This is a simple change but important for the templates to work correctly.
```

### Step 2.1: Create Test Directory Structure

```text
Create a comprehensive test directory structure in the {{ cookiecutter.project_slug }} directory. Please create:

1. A tests/ directory at the project root level
2. Add __init__.py files in all test directories
3. Create subdirectories:
   - tests/test_core/ (for testing the core app)
   - tests/test_api/ (for future API tests)
   - tests/integration/ (for integration tests)
   - tests/fixtures/ (for test data)
4. Add a .gitkeep file in empty directories

The structure should be logical and scalable for a growing project.
```

### Step 2.2: Add Test Configuration

```text
Create test configuration files in the {{ cookiecutter.project_slug }} directory. Please:

1. Create tests/conftest.py with:
   - Basic pytest fixtures (client, admin_client)
   - Database fixtures
   - User fixtures
   - Any helper fixtures
2. Ensure test database settings work with PostgreSQL
3. Add any test-specific Django settings if needed
4. Configure pytest-django properly

The configuration should make writing tests easy and consistent.
```

### Step 2.3: Create Test Factories

```text
Create factory-boy factories for testing in the {{ cookiecutter.project_slug }} directory. Please:

1. Create tests/factories.py (or tests/factories/ package if complex)
2. Add a UserFactory for the Django User model
3. Create base factory classes that other factories can inherit from
4. Add any helper methods for common patterns
5. Include examples of different factory patterns (SubFactory, post_generation, etc.)

The factories should follow factory-boy best practices and be easy to extend.
```

### Step 2.4: Write Example Tests

```text
Create example tests in the {{ cookiecutter.project_slug }} directory to demonstrate testing patterns. Please create:

1. tests/test_core/test_views.py with:
   - Test for home view
   - Test for about view
   - Test for 404 handling
2. tests/test_core/test_models.py with:
   - Example model tests (when models are added)
   - Test structure for future use
3. tests/integration/test_pages.py with:
   - Full page load tests
   - Static file serving tests

Use pytest style (not unittest) and include docstrings explaining the testing patterns.
```

### Step 2.5: Add Coverage Configuration

```text
Configure code coverage for the {{ cookiecutter.project_slug }} project. Please:

1. Update pyproject.toml with pytest-cov configuration:
   - Set coverage source paths
   - Configure coverage reporting
   - Set minimum coverage threshold (80%)
2. Create .coveragerc file with:
   - Omit patterns for files to exclude
   - Coverage report settings
   - HTML report configuration
3. Update the Makefile with coverage commands:
   - make test-coverage
   - make coverage-html
   - make coverage-report

The configuration should make it easy to maintain high code coverage.
```

### Step 3.1: Create Pre-commit Configuration

```text
Create a .pre-commit-config.yaml file in the {{ cookiecutter.project_slug }} directory with basic hooks. Please include:

1. Pre-commit framework setup
2. Ruff for linting and formatting:
   - ruff check
   - ruff format
3. Basic file checks:
   - trailing-whitespace
   - end-of-file-fixer
   - check-yaml
   - check-json
   - check-merge-conflict
4. Set appropriate Python version
5. Configure hook stages appropriately

The configuration should be strict but not annoying for developers.
```

### Step 3.2: Add Additional Pre-commit Hooks

```text
Enhance the .pre-commit-config.yaml in the {{ cookiecutter.project_slug }} directory with additional quality checks. Please add:

1. A local hook to run pytest on staged files
2. File size limit check
3. Security checks (detect-private-key, etc.)
4. Django-specific checks if available
5. Documentation checks (if applicable)

Make sure the hooks are ordered logically and fail fast on critical issues.
```

### Step 3.3: Update Development Workflow

```text
Update the development workflow documentation and tools in the {{ cookiecutter.project_slug }} directory to include pre-commit. Please:

1. Update README with pre-commit installation instructions
2. Add Makefile commands:
   - make install-pre-commit
   - make run-pre-commit
3. Update any development setup documentation
4. Add troubleshooting tips for common pre-commit issues

The documentation should make it easy for new developers to get started.
```

### Step 4.1: Add Security Middleware

```text
Update the settings.py (or settings package) in the {{ cookiecutter.project_slug }} directory to add Django security middleware. Please:

1. Ensure SecurityMiddleware is in MIDDLEWARE
2. Add security-related settings:
   - SECURE_BROWSER_XSS_FILTER
   - SECURE_CONTENT_TYPE_NOSNIFF
   - X_FRAME_OPTIONS
3. Configure settings appropriately for development vs production
4. Add comments explaining each security setting

The configuration should improve security without breaking development.
```

### Step 4.2: Configure Security Headers

```text
Add comprehensive security headers configuration to the {{ cookiecutter.project_slug }} settings. Please:

1. Configure HSTS (HTTP Strict Transport Security):
   - SECURE_HSTS_SECONDS
   - SECURE_HSTS_INCLUDE_SUBDOMAINS
   - SECURE_HSTS_PRELOAD
2. Add CSP (Content Security Policy) configuration:
   - Install django-csp if needed
   - Configure basic CSP rules
3. Add other security headers:
   - Referrer-Policy
   - Permissions-Policy
4. Make headers environment-specific

The configuration should be secure but not break modern web features.
```

### Step 4.3: Secure Cookie Settings

```text
Update cookie security settings in the {{ cookiecutter.project_slug }} settings. Please:

1. Add secure cookie settings:
   - SESSION_COOKIE_SECURE (production only)
   - CSRF_COOKIE_SECURE (production only)
   - SESSION_COOKIE_HTTPONLY
   - CSRF_COOKIE_HTTPONLY
2. Configure cookie age and expiry:
   - SESSION_COOKIE_AGE
   - SESSION_EXPIRE_AT_BROWSER_CLOSE
3. Add SameSite cookie settings:
   - SESSION_COOKIE_SAMESITE
   - CSRF_COOKIE_SAMESITE
4. Use environment variables for production detection

The settings should be secure in production but work in development.
```

### Step 4.4: Add CORS Configuration

```text
Add CORS (Cross-Origin Resource Sharing) configuration to the {{ cookiecutter.project_slug }} project. Please:

1. Add django-cors-headers to pyproject.toml dependencies
2. Add to INSTALLED_APPS
3. Add CorsMiddleware to MIDDLEWARE (in correct position)
4. Configure CORS settings:
   - CORS_ALLOWED_ORIGINS (from environment)
   - CORS_ALLOW_CREDENTIALS
   - CORS_ALLOW_HEADERS
   - CORS_ALLOW_METHODS
5. Add development vs production configuration

The configuration should be secure by default but configurable via environment.
```

### Step 5.1: Create API App Structure

```text
Create a Django Ninja API app structure in the {{ cookiecutter.project_slug }} directory. Please:

1. Create an api/ directory at the project root
2. Add __init__.py to make it a Python package
3. Create subdirectories:
   - api/v1/ (for version 1 of the API)
   - api/v1/endpoints/ (for endpoint modules)
   - api/v1/schemas/ (for Pydantic schemas)
4. Add __init__.py files in all directories
5. Create api/urls.py for API URL configuration

The structure should support API versioning and clean organization.
```

### Step 5.2: Configure Django Ninja

```text
Configure Django Ninja in the {{ cookiecutter.project_slug }} project. Please:

1. Add django-ninja to pyproject.toml dependencies
2. Create api/v1/api.py with:
   - NinjaAPI instance creation
   - Basic configuration (title, version, description)
   - URL versioning setup
3. Update main urls.py to include API URLs:
   - Add path for api/
   - Include api.urls
4. Create api/urls.py to wire up the API

The configuration should be clean and support future API expansion.
```

### Step 5.3: Create Example Endpoints

```text
Create example Django Ninja endpoints in the {{ cookiecutter.project_slug }} project. Please:

1. Create api/v1/endpoints/health.py with:
   - Simple health check endpoint
   - Status endpoint with debug info
2. Create api/v1/endpoints/auth.py with:
   - Login endpoint example
   - User info endpoint (authenticated)
3. Create api/v1/schemas/common.py with:
   - Common response schemas
   - Error response schemas
4. Wire up endpoints in api/v1/api.py

The endpoints should demonstrate common patterns and best practices.
```

### Step 5.4: Add API Documentation

```text
Configure API documentation for Django Ninja in the {{ cookiecutter.project_slug }} project. Please:

1. Ensure OpenAPI/Swagger documentation is enabled
2. Add custom documentation configuration:
   - API title and description
   - Version information
   - Contact details
3. Configure authentication documentation
4. Add example request/response documentation to endpoints
5. Ensure docs are only available in development by default

The documentation should be comprehensive and helpful for API users.
```

### Step 6.1: Create Settings Package

```text
Refactor settings.py into a settings package in the {{ cookiecutter.project_slug }} project. Please:

1. Create core/settings/ directory
2. Create __init__.py that imports from appropriate settings module
3. Move current settings.py content to settings/base.py
4. Create settings/development.py that:
   - Imports from base
   - Overrides development-specific settings
5. Create settings/production.py that:
   - Imports from base
   - Adds production-specific settings
6. Update manage.py and wsgi.py to use new settings structure

The refactoring should make settings management cleaner and more maintainable.
```

### Step 6.2: Environment Validation

```text
Add environment variable validation to the {{ cookiecutter.project_slug }} settings. Please:

1. Create a validation function for required environment variables
2. Add validation for:
   - DATABASE_URL (required in production)
   - SECRET_KEY (required always)
   - ALLOWED_HOSTS (required in production)
   - Any other critical variables
3. Provide helpful error messages when variables are missing
4. Add type validation where appropriate
5. Document all environment variables in .env.example

The validation should catch configuration errors early with clear messages.
```

### Step 6.3: Logging Configuration

```text
Add comprehensive logging configuration to the {{ cookiecutter.project_slug }} settings. Please:

1. Create a LOGGING configuration dictionary with:
   - Formatters (including structured logging option)
   - Handlers (console, file, etc.)
   - Loggers for different components
2. Configure different log levels for development vs production
3. Add request ID middleware for log correlation
4. Include SQL query logging in development
5. Add comments explaining the logging setup

The logging should be helpful for debugging and production monitoring.
```

### Step 7.1: Enhance Makefile

```text
Enhance the Makefile in the {{ cookiecutter.project_slug }} directory with more development commands. Please add:

1. Test-related commands:
   - make test-fast (without coverage)
   - make test-failed (rerun failed tests)
   - make test-watch (if possible)
2. Development commands:
   - make shell (Django shell)
   - make shell-plus (if available)
   - make migrate
   - make migrations
3. Code quality commands:
   - make lint
   - make format
   - make type-check (if using mypy)
4. Utility commands:
   - make clean (remove artifacts)
   - make requirements (update dependencies)

Keep existing commands and ensure all commands have help text.
```

### Step 7.2: Add ABOUTME Comments

```text
Add ABOUTME comments to all Python files in the {{ cookiecutter.project_slug }} project. Please:

1. Add a 2-line comment at the top of each Python file
2. Start each line with "ABOUTME: "
3. Briefly explain what the file does
4. Examples:
   - "ABOUTME: Main URL configuration for the project."
   - "ABOUTME: Handles routing for all application endpoints."
5. Cover all Python files in:
   - core/
   - api/ (if created)
   - Project root (manage.py, etc.)

The comments should be concise and helpful for understanding file purposes.
```

### Step 7.3: Create Comprehensive Documentation

```text
Create comprehensive documentation for the {{ cookiecutter.project_slug }} project. Please:

1. Update README.md with:
   - Project overview
   - Quick start guide
   - Development setup
   - Testing instructions
   - Deployment guide
2. Create docs/ARCHITECTURE.md with:
   - Project structure explanation
   - Design decisions
   - API design
   - Database schema overview
3. Create docs/DEVELOPMENT.md with:
   - Development workflow
   - Code style guide
   - Testing practices
   - Troubleshooting

The documentation should be clear, concise, and helpful for new developers.
```

### Step 8.1: Create GitHub Actions Workflow

```text
Create a GitHub Actions CI workflow in the {{ cookiecutter.project_slug }} project. Please:

1. Create .github/workflows/ci.yml
2. Add workflow triggers (push, pull_request)
3. Create jobs for:
   - Running tests with pytest
   - Running linting with ruff
   - Checking code formatting
4. Use PostgreSQL service for tests
5. Cache dependencies for faster runs
6. Set up Python and uv correctly

The workflow should be efficient and provide quick feedback.
```

### Step 8.2: Add Advanced CI Features

```text
Enhance the GitHub Actions workflow in the {{ cookiecutter.project_slug }} project. Please add:

1. Security scanning job:
   - Dependency vulnerability scanning
   - Security linting
2. Coverage reporting:
   - Upload coverage reports
   - Add coverage badge to README
3. Matrix testing:
   - Test against multiple Python versions
   - Test against multiple Django versions
4. Deployment job (if applicable):
   - Deploy to staging on main branch
   - Production deployment tags

The enhancements should improve code quality and security.
```

### Step 9.1: Debug Toolbar Configuration

```text
Configure django-debug-toolbar in the {{ cookiecutter.project_slug }} project. Please:

1. Ensure django-debug-toolbar is in dev dependencies
2. Add to INSTALLED_APPS (development only)
3. Add debug toolbar middleware (development only)
4. Configure INTERNAL_IPS for toolbar display
5. Add debug toolbar URLs (development only)
6. Configure toolbar panels
7. Add documentation for using the toolbar

The toolbar should only be available in development and be helpful for debugging.
```

### Step 9.2: Performance Optimizations

```text
Add performance optimization examples to the {{ cookiecutter.project_slug }} project. Please:

1. Create examples/caching.py with:
   - Cache configuration examples
   - View caching examples
   - Template fragment caching
2. Create examples/database_optimization.py with:
   - Select_related and prefetch_related examples
   - Database indexing tips
   - Query optimization patterns
3. Create examples/async_views.py with:
   - Async view examples
   - Async database queries
   - Best practices for async Django
4. Add performance tips to documentation

The examples should be practical and well-documented.
```

## Implementation Tracking

Each step should be tracked in 02_TODO.md with:
1. Step ID and description
2. GitHub issue reference (if created)
3. Implementation status (pending/in-progress/completed)
4. Any blockers or notes

## Success Criteria

Each step is considered complete when:
1. Code changes are implemented
2. Tests pass (if applicable)
3. Pre-commit hooks pass
4. Documentation is updated
5. No regressions are introduced

## Next Steps

1. Review this plan for completeness
2. Create GitHub issues for each major phase
3. Begin implementation with Phase 0
4. Track progress in 02_TODO.md