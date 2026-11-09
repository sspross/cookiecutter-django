from core.tests.fresh_settings import production_settings

COOKIE_NAMES = ["SESSION_COOKIE_NAME", "CSRF_COOKIE_NAME"]


def cookie_names(**overrides: str) -> dict[str, object]:
    return production_settings(COOKIE_NAMES, unset=COOKIE_NAMES, **overrides)


def test_cookie_names_default_to_djangos() -> None:
    assert cookie_names() == {
        "SESSION_COOKIE_NAME": "sessionid",
        "CSRF_COOKIE_NAME": "csrftoken",
    }


def test_cookie_names_come_from_the_environment() -> None:
    assert cookie_names(
        SESSION_COOKIE_NAME="sessionid_8001", CSRF_COOKIE_NAME="csrftoken_8001"
    ) == {
        "SESSION_COOKIE_NAME": "sessionid_8001",
        "CSRF_COOKIE_NAME": "csrftoken_8001",
    }
