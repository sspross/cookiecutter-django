"""URL configuration for the project.

The mount order matters: API and admin are matched first, then media (in
DEBUG only — in deploy media is served by the operator's external reverse
proxy from a bind-mounted volume), then a re-path catch-all for the SPA
shell.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path

from core.api import api
from core.views import spa_shell

urlpatterns = [
    path("api/", api.urls),
    path("admin/", admin.site.urls),
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
    re_path(r"^(?!api/|admin/|static/|media/).*$", spa_shell, name="spa-shell"),
]
