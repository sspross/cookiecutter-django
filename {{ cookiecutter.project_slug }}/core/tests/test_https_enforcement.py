import pytest

from core.tests.fresh_settings import production_settings

ENFORCED = {
    "SECURE_SSL_REDIRECT": True,
    "SESSION_COOKIE_SECURE": True,
    "CSRF_COOKIE_SECURE": True,
    "SECURE_HSTS_SECONDS": 60 * 60 * 24 * 365,
}
NOT_ENFORCED = {
    "SECURE_SSL_REDIRECT": False,
    "SESSION_COOKIE_SECURE": False,
    "CSRF_COOKIE_SECURE": False,
    "SECURE_HSTS_SECONDS": 0,
}


def https_settings(**overrides: str) -> dict[str, object]:
    return production_settings(ENFORCED, unset=["HTTPS_ENFORCED"], **overrides)


def test_https_is_enforced_by_default() -> None:
    assert https_settings() == ENFORCED


@pytest.mark.parametrize("value", ["", "0", "no", "off", "False "])
def test_https_stays_enforced_unless_the_value_is_exactly_false(value: str) -> None:
    assert https_settings(HTTPS_ENFORCED=value) == ENFORCED


@pytest.mark.parametrize("value", ["false", "FALSE"])
def test_https_enforcement_is_off_only_with_an_explicit_false(value: str) -> None:
    assert https_settings(HTTPS_ENFORCED=value) == NOT_ENFORCED
