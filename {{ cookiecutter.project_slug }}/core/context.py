from django.conf import settings
from django.http import HttpRequest


def site(request: HttpRequest) -> dict:
    """Inject site-wide values (project name) into all templates."""
    return {
        "project_name": settings.PROJECT_NAME,
    }
