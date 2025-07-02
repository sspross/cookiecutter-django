# 01_SPEC.md - Cookiecutter Django Template Improvement Specification

## Executive Summary

This document outlines the comprehensive improvements needed for the cookiecutter-django template to meet modern Django development standards. The template will be refactored to use Django templates exclusively, Django Ninja for APIs, and include a robust testing infrastructure with pre-commit hooks.

## Project Goals

1. Create a production-ready Django template for internal use
2. Enforce code quality through automation
3. Include modern Django best practices
4. Maintain simplicity while being comprehensive
5. Support monolithic architecture with clean internal separation

## Decided Technology Stack

Based on our discussion, here are the final technology decisions:

### Core Technologies
- **Python**: 3.12+
- **Django**: 5.1.2+
- **Package Manager**: uv (no Poetry, pip, or pip-tools)
- **Database**: PostgreSQL
- **Templates**: Django templates only (remove Jinja2)
- **API Framework**: Django Ninja
- **Static Files**: WhiteNoise
- **Production Server**: Gunicorn
- **Deployment**: Appliku.com (for now)

### Development Tools
- **Linting/Formatting**: ruff
- **Testing**: pytest + pytest-django + factory-boy
- **Coverage**: pytest-cov (target: 80%)
- **Pre-commit**: Automated quality checks
- **Debug**: django-debug-toolbar

## Implementation Plan

### Phase 1: Core Infrastructure (High Priority)

#### 1.1 Testing Infrastructure
- Create `tests/` directory structure
- Add test fixtures and factories
- Write example tests for views, models, and API endpoints
- Configure pytest with Django settings
- Add coverage configuration (80% target)

#### 1.2 Pre-commit Configuration
- Add `.pre-commit-config.yaml`
- Include hooks for:
  - ruff (linting and formatting)
  - pytest (failing tests)
  - Check for merge conflicts
  - Check YAML/JSON syntax
  - Trailing whitespace
  - File size limits

#### 1.3 Remove Jinja2
- Remove django-jinja from dependencies
- Update settings.py to use only Django templates
- Convert any Jinja2 templates to Django template syntax
- Update template configuration

#### 1.4 Security Improvements
- Add security middleware
- Configure security headers (HSTS, CSP, etc.)
- Add secure cookie settings
- Implement proper CORS configuration
- Add rate limiting setup

### Phase 2: API & Architecture (High Priority)

#### 2.1 Django Ninja Integration
- Add Django Ninja to dependencies
- Create `api/` app structure
- Add example API endpoints
- Include OpenAPI documentation setup
- Add API versioning structure

#### 2.2 Settings Refactoring
- Create settings package with base/dev/prod modules
- Add validation for required environment variables
- Improve secret key generation
- Add proper logging configuration

#### 2.3 Code Organization
- Add ABOUTME comments to all Python files
- Create proper app structure examples
- Add domain-driven design patterns
- Document internal service boundaries

### Phase 3: Developer Experience (Medium Priority)

#### 3.1 Improve .gitignore
- Add comprehensive Python patterns
- Include IDE files (.idea/, .vscode/)
- Add OS-specific files
- Include test/coverage artifacts

#### 3.2 Enhanced Makefile
- Add more development commands
- Include test running shortcuts
- Add migration helpers
- Include linting/formatting commands

#### 3.3 Documentation
- Create comprehensive README
- Add architecture documentation
- Include development workflow guide
- Add troubleshooting section

#### 3.4 GitHub Actions CI/CD
- Add workflow for tests
- Include linting checks
- Add security scanning
- Configure dependency updates

### Phase 4: Advanced Features (Nice to Have)

#### 4.1 Monitoring & Observability
- Add structured logging setup
- Include health check endpoints
- Add basic metrics collection
- Prepare for error tracking (Sentry)

#### 4.2 Performance Optimization
- Add Redis configuration example
- Include caching patterns
- Add database optimization tips
- Include async view examples

#### 4.3 Development Tools
- Add debug toolbar configuration
- Include profiling setup
- Add database query optimization tools
- Include performance testing examples

## File Structure After Implementation

```
{{ cookiecutter.project_slug }}/
├── api/                        # Django Ninja API
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   └── schemas/
│   └── urls.py
├── core/                       # Main Django app
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── views.py
│   ├── models.py
│   └── templates/
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── factories.py
│   ├── test_api/
│   ├── test_models/
│   └── test_views/
├── static/
├── media/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .pre-commit-config.yaml
├── .gitignore
├── .env.example
├── Dockerfile
├── Makefile
├── README.md
├── manage.py
├── pyproject.toml
├── pytest.ini
└── uv.lock
```

## Implementation Order

1. **Immediate fixes**:
   - Fix Dockerfile to use uv
   - Fix pyproject.toml dependencies

2. **Next steps** (High priority):
   - Remove Jinja2 and update templates
   - Add comprehensive test structure
   - Create pre-commit configuration
   - Implement security headers

3. **Follow-up** (Medium priority):
   - Add Django Ninja API structure
   - Refactor settings into modules
   - Add ABOUTME comments
   - Create GitHub Actions workflow

4. **Polish** (Low priority):
   - Add monitoring setup
   - Include performance optimizations
   - Add advanced development tools

## Success Metrics

1. **Code Quality**
   - All code passes ruff linting
   - Tests achieve 80% coverage
   - Pre-commit hooks prevent bad commits
   - Zero security vulnerabilities

2. **Developer Experience**
   - New project setup in < 5 minutes
   - Clear documentation for all features
   - Automated quality checks
   - Consistent code style

3. **Production Readiness**
   - Secure by default
   - Performance optimized
   - Deployment ready
   - Monitoring prepared

## Current Status

**No phases have been completed yet.** All implementation phases are pending.

## Next Actions

1. Remove django-jinja and update template configuration
2. Create test directory structure with examples
3. Add pre-commit configuration
4. Implement security improvements
5. Add Django Ninja API structure
6. Improve .gitignore with comprehensive patterns

This specification provides a clear roadmap for transforming the cookiecutter-django template into a modern, production-ready Django project starter that follows best practices while maintaining simplicity.