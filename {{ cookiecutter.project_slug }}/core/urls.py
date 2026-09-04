from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core import views
from core.api import api

urlpatterns = [
    # Every URL the React router knows needs a server-side match here, or a
    # hard reload 404s instead of returning the SPA shell.
    path("", views.app_view, name="home"),
    path("api-access/", views.app_view),
    path("api/", api.urls),
    # Mounted one by one instead of `include("django.contrib.auth.urls")`:
    # only login and logout have a template here, so the rest of that URLconf
    # would 500 on a missing template instead of 404. Adding password change
    # or reset means adding its templates and a mailer first.
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    # django-rq gates this dashboard to staff itself, so no decorator here.
    path("django-rq/", include("django_rq.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
