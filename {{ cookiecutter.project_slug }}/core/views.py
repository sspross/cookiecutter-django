from dataclasses import dataclass

from django.http import HttpRequest
from django.shortcuts import render
from django.urls import reverse


@dataclass
class Navitem:
    name: str
    label: str

    @property
    def url(self) -> str:
        return reverse(self.name)


NAVITEMS = [
    Navitem(name="home", label="Home"),
    Navitem(name="about", label="About"),
]

PROJECT_NAME = "{{ cookiecutter.project_name }}"


def home(request: HttpRequest):
    return render(
        request, "home.html", {"navitems": NAVITEMS, "project_name": PROJECT_NAME}
    )


def about(request: HttpRequest):
    return render(
        request, "about.html", {"navitems": NAVITEMS, "project_name": PROJECT_NAME}
    )
