from django.http import HttpRequest
from django.shortcuts import render


def home(request: HttpRequest):
    return render(request, "home.jinja")


def about(request: HttpRequest):
    return render(request, "about.jinja")
