import re

from django.conf import settings
from django.urls import Resolver404, resolve

from core import views

FRONTEND = settings.BASE_DIR / "core" / "frontend"


def spa_route_paths() -> list[str]:
    app = (FRONTEND / "src" / "spa" / "App.tsx").read_text()
    return re.findall(r'<Route\s+path="([^"]+)"', app)


def serves_the_spa_mount(route: str) -> bool:
    try:
        return resolve(route.rstrip("/") + "/").func is views.app_view
    except Resolver404:
        return False


def test_spa_routes_are_found_so_the_check_cannot_pass_empty() -> None:
    assert "/api-access" in spa_route_paths()


def test_every_spa_route_is_a_django_route_so_a_hard_reload_does_not_404() -> None:
    not_mounted = [
        route for route in spa_route_paths() if not serves_the_spa_mount(route)
    ]

    assert not_mounted == []


def test_vite_base_is_where_django_vite_looks_for_the_bundle() -> None:
    vite_config = (FRONTEND / "vite.config.mjs").read_text()
    (base,) = re.findall(r'\bbase:\s*"([^"]+)"', vite_config)
    static_url_prefix = settings.DJANGO_VITE["default"]["static_url_prefix"]

    assert base == f"{settings.STATIC_URL}{static_url_prefix}/"
