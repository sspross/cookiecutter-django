from django.conf import settings
from django.http import HttpRequest


def site(request: HttpRequest) -> dict:
    return {
        "project_name": settings.PROJECT_NAME,
    }
