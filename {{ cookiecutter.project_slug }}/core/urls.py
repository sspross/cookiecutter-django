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
    # Mounted one by one rather than `include("django.contrib.auth.urls")`:
    # the rest of that URLconf has no template here. See CONTEXT.md.
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    # django-rq gates this dashboard to staff itself, so no decorator here.
    path("django-rq/", include("django_rq.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
