from allauth.socialaccount.providers.google import views as google_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, reverse_lazy
from django.views.generic import RedirectView

from core import views
from core.api import api

urlpatterns = [
    # In lockstep with the routes in core/frontend/src/spa/App.tsx: a route missing
    # here 404s on a hard reload.
    path("", views.app_view, name="home"),
    path("api-access/", views.app_view),
    path("api/", api.urls),
    path("healthz", views.healthz, name="healthz"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "admin/login/",
        RedirectView.as_view(url=reverse_lazy("login"), query_string=True),
    ),
    path("admin/", admin.site.urls),
    # django-rq gates this dashboard to staff itself, so no decorator here.
    path("django-rq/", include("django_rq.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.SOCIALACCOUNT_PROVIDERS:
    urlpatterns += [
        path(
            "accounts/google/login/",
            google_views.oauth2_login,
            name="google_login",
        ),
        path(
            "accounts/google/login/callback/",
            google_views.oauth2_callback,
            name="google_callback",
        ),
    ]
