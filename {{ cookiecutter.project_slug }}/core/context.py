from dataclasses import dataclass

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse


@dataclass
class Navitem:
    name: str
    label: str

    @property
    def url(self) -> str:
        return reverse(self.name)


NAVITEMS = [
    Navitem(name="home", label="Dashboard"),
    Navitem(name="api-access", label="API Access"),
]


def site(request: HttpRequest) -> dict:
    """Inject site-wide values (project name, nav items) into all templates."""
    return {
        "navitems": NAVITEMS,
        "project_name": settings.PROJECT_NAME,
    }
