from django.conf import settings
from django.http import HttpRequest


def site(request: HttpRequest) -> dict[str, str]:
    return {
        "project_name": settings.PROJECT_NAME,
        "csrf_cookie_name": settings.CSRF_COOKIE_NAME,
    }
