from django.http import HttpRequest
from django.shortcuts import render


def home(request: HttpRequest):
    return render(request, "home.html")


def about(request: HttpRequest):
    return render(request, "about.html")
