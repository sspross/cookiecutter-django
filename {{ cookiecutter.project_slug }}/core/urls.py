"""URL configuration for the project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from core import views
from core.api import api

urlpatterns = [
    # SPA routes: every URL the React router knows about needs a server-side
    # match here so a hard reload returns the SPA shell instead of a 404.
    path("", views.app_view, name="home"),
    path("api-access/", views.app_view),
    path("api/", api.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("admin/", admin.site.urls),
    # django-rq's queue dashboard. Access is gated by django-rq itself
    # to staff users only, so it's safe to mount at the project root.
    path("django-rq/", include("django_rq.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
