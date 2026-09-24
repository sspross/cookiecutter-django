"""The Google login flow over HTTP. Only Google's token endpoint is stubbed;
allauth, the adapter, the allowlist and the settings run for real."""

import time
import uuid
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
import responses
from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.core.management import call_command
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

from api_keys.tests.factories import UserFactory
from users.models import User
from users.sso import CANCELLED_MESSAGE, FAILED_MESSAGE, NOT_ALLOWED_MESSAGE

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _start(client: Client, next_url: str | None) -> str:
    """POST to the Google login URL and return the state Google would echo."""
    data = {"next": next_url} if next_url else {}
    response = client.post(reverse("google_login"), data)
    assert response.status_code == 302
    assert response["Location"].startswith("https://accounts.google.com/")
    return parse_qs(urlparse(response["Location"]).query)["state"][0]


def _id_token(email: str, email_verified: bool, hd: str | None) -> str:
    """Unsigned is fine: allauth skips the signature check for an ID token it
    fetched from Google's token endpoint itself, over TLS."""
    claims = {
        "iss": "https://accounts.google.com",
        "aud": settings.SOCIALACCOUNT_PROVIDERS["google"]["APP"]["client_id"],
        "sub": str(uuid.uuid5(uuid.NAMESPACE_URL, email)),
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
        "email": email,
        "email_verified": email_verified,
        "given_name": "Test",
    }
    if hd is not None:
        claims["hd"] = hd
    return jwt.encode(claims, "never-verified-" + "x" * 32, algorithm="HS256")


def sign_in_with_google(
    client: Client,
    email: str,
    *,
    email_verified: bool = True,
    hd: str | None = None,
    next_url: str | None = None,
) -> HttpResponse:
    """The whole round trip: the login button's POST, Google's redirect back
    to the callback, and the token exchange behind it."""
    state = _start(client, next_url)
    with responses.RequestsMock() as google:
        google.post(
            GOOGLE_TOKEN_URL,
            json={
                "access_token": "access-token",
                "expires_in": 3600,
                "token_type": "Bearer",
                "id_token": _id_token(email, email_verified, hd),
            },
        )
        return client.get(reverse("google_callback"), {"code": "code", "state": state})


def logged_in_user(client: Client) -> User | None:
    user_id = client.session.get(SESSION_KEY)
    return User.objects.get(pk=user_id) if user_id else None


def assert_rejected(client: Client, response: HttpResponse, message: str) -> None:
    assert response.status_code == 302
    assert response["Location"] == reverse("login")
    assert logged_in_user(client) is None
    login_page = client.get(response["Location"])
    assert message in login_page.content.decode()


@pytest.fixture
def allowlist(settings):
    settings.SSO_ALLOWED_DOMAINS = ["company.com"]
    settings.SSO_ALLOWED_EMAILS = ["guest@gmail.com"]
    settings.SSO_SUPERUSER_EMAILS = ["Boss@company.com"]
    return settings


@pytest.mark.django_db
class TestAllowedGoogleLogin:
    def test_workspace_domain_via_hd_logs_in_and_creates_the_user(
        self, client, allowlist
    ):
        response = sign_in_with_google(client, "anna@company.com", hd="company.com")

        assert response.status_code == 302
        assert response["Location"] == reverse("home")
        user = logged_in_user(client)
        assert user is not None
        assert user.email == "anna@company.com"
        assert user.username == "anna@company.com"
        assert not user.has_usable_password()

    def test_same_local_part_on_two_domains_gets_two_usernames(self, client, allowlist):
        allowlist.SSO_ALLOWED_EMAILS = ["anna@gmail.com"]
        sign_in_with_google(client, "anna@company.com", hd="company.com")
        client.logout()

        sign_in_with_google(client, "anna@gmail.com")

        assert logged_in_user(client).username == "anna@gmail.com"
        assert User.objects.filter(username="anna@company.com").exists()

    def test_single_email_logs_in(self, client, allowlist):
        sign_in_with_google(client, "Guest@gmail.com")

        assert logged_in_user(client).email == "guest@gmail.com"

    def test_returns_to_the_requested_page(self, client, allowlist):
        response = sign_in_with_google(
            client, "anna@company.com", hd="company.com", next_url="/api-access/"
        )

        assert response["Location"] == "/api-access/"

    def test_superuser_email_is_created_as_superuser_and_staff(self, client, allowlist):
        sign_in_with_google(client, "boss@company.com", hd="company.com")

        user = logged_in_user(client)
        assert user.is_superuser
        assert user.is_staff

    def test_other_emails_are_never_promoted(self, client, allowlist):
        sign_in_with_google(client, "anna@company.com", hd="company.com")

        user = logged_in_user(client)
        assert not user.is_superuser
        assert not user.is_staff

    def test_links_to_an_existing_user_with_the_same_email(self, client, allowlist):
        existing = UserFactory(username="guest", email="guest@gmail.com")

        sign_in_with_google(client, "guest@gmail.com")

        assert logged_in_user(client) == existing
        assert User.objects.filter(email__iexact="guest@gmail.com").count() == 1

    def test_leaves_no_message_for_the_next_login_page(self, client, allowlist):
        sign_in_with_google(client, "guest@gmail.com")
        client.post(reverse("logout"))

        login_page = client.get(reverse("login"))

        assert 'data-testid="login-message"' not in login_page.content.decode()

    def test_linking_promotes_an_existing_user_on_the_superuser_list(
        self, client, allowlist
    ):
        existing = UserFactory(username="boss", email="boss@company.com")

        sign_in_with_google(client, "boss@company.com", hd="company.com")

        existing.refresh_from_db()
        assert logged_in_user(client) == existing
        assert existing.is_superuser
        assert existing.is_staff

    def test_user_added_to_the_superuser_list_is_promoted_on_next_login(
        self, client, allowlist
    ):
        sign_in_with_google(client, "guest@gmail.com")
        client.logout()
        allowlist.SSO_SUPERUSER_EMAILS = ["guest@gmail.com"]

        sign_in_with_google(client, "guest@gmail.com")

        user = logged_in_user(client)
        assert user.is_superuser
        assert user.is_staff

    def test_removal_from_the_superuser_list_does_not_demote(self, client, allowlist):
        sign_in_with_google(client, "boss@company.com", hd="company.com")
        client.logout()
        allowlist.SSO_SUPERUSER_EMAILS = []

        sign_in_with_google(client, "boss@company.com", hd="company.com")

        user = logged_in_user(client)
        assert user.is_superuser
        assert user.is_staff


def log_in_with_password(client: Client, username: str, password: str) -> None:
    response = client.post(
        reverse("login"), {"username": username, "password": password}
    )
    assert response.status_code == 302
    assert logged_in_user(client).username == username


@pytest.mark.django_db
class TestPasswordSurvivesGoogleLogin:
    def test_user_added_in_the_admin(self, client, admin_client, allowlist):
        admin_client.post(
            reverse("admin:users_user_add"),
            {
                "username": "guest",
                "email": "guest@gmail.com",
                "usable_password": "true",
                "password1": "pw-12345!guest",
                "password2": "pw-12345!guest",
            },
        )

        sign_in_with_google(client, "guest@gmail.com")
        assert logged_in_user(client).username == "guest"
        client.logout()

        log_in_with_password(client, "guest", "pw-12345!guest")

    def test_user_added_in_the_admin_with_a_capitalized_email_is_linked(
        self, client, admin_client, allowlist
    ):
        admin_client.post(
            reverse("admin:users_user_add"),
            {
                "username": "guest",
                "email": "Guest@gmail.com",
                "usable_password": "true",
                "password1": "pw-12345!guest",
                "password2": "pw-12345!guest",
            },
        )

        sign_in_with_google(client, "guest@gmail.com")

        assert logged_in_user(client).username == "guest"
        assert User.objects.filter(email__iexact="guest@gmail.com").count() == 1

    def test_user_from_createsuperuser(self, client, allowlist, monkeypatch):
        monkeypatch.setenv("DJANGO_SUPERUSER_PASSWORD", "pw-12345!boss")
        call_command(
            "createsuperuser",
            interactive=False,
            username="boss",
            email="boss@company.com",
        )

        sign_in_with_google(client, "boss@company.com", hd="company.com")
        assert logged_in_user(client).username == "boss"
        client.logout()

        log_in_with_password(client, "boss", "pw-12345!boss")


@pytest.mark.django_db
class TestRejectedGoogleLogin:
    def test_unlisted_email_is_rejected_with_a_message(self, client, allowlist):
        response = sign_in_with_google(client, "stranger@gmail.com")

        assert_rejected(client, response, NOT_ALLOWED_MESSAGE)
        assert not User.objects.filter(email="stranger@gmail.com").exists()

    def test_superuser_email_alone_does_not_allow_a_login(self, client, allowlist):
        allowlist.SSO_SUPERUSER_EMAILS = ["outsider@gmail.com"]

        response = sign_in_with_google(client, "outsider@gmail.com")

        assert_rejected(client, response, NOT_ALLOWED_MESSAGE)
        assert not User.objects.filter(email="outsider@gmail.com").exists()

    def test_allowed_domain_without_hd_claim_is_rejected(self, client, allowlist):
        response = sign_in_with_google(client, "private@company.com")

        assert_rejected(client, response, NOT_ALLOWED_MESSAGE)
        assert not User.objects.filter(email="private@company.com").exists()

    def test_unverified_email_is_rejected(self, client, allowlist):
        response = sign_in_with_google(
            client, "anna@company.com", email_verified=False, hd="company.com"
        )

        assert_rejected(client, response, NOT_ALLOWED_MESSAGE)

    def test_removal_from_the_allowlist_blocks_the_next_login(self, client, allowlist):
        sign_in_with_google(client, "guest@gmail.com")
        client.logout()
        allowlist.SSO_ALLOWED_EMAILS = []

        response = sign_in_with_google(client, "guest@gmail.com")

        assert_rejected(client, response, NOT_ALLOWED_MESSAGE)
        assert User.objects.filter(email="guest@gmail.com").count() == 1

    def test_inactive_existing_user_is_rejected(self, client, allowlist):
        UserFactory(username="guest", email="guest@gmail.com", is_active=False)

        response = sign_in_with_google(client, "guest@gmail.com")

        assert_rejected(client, response, NOT_ALLOWED_MESSAGE)

    def test_rejection_is_logged_with_email_and_reason(self, client, allowlist, caplog):
        with caplog.at_level("INFO", logger="users"):
            sign_in_with_google(client, "stranger@gmail.com")

        assert (
            "Rejected Google login for stranger@gmail.com: not on the SSO allowlist"
            in caplog.text
        )

    def test_cancel_on_googles_consent_screen_returns_to_login(self, client):
        state = _start(client, None)

        response = client.get(
            reverse("google_callback"), {"error": "access_denied", "state": state}
        )

        assert_rejected(client, response, CANCELLED_MESSAGE)

    def test_failed_token_exchange_returns_to_login(self, client):
        state = _start(client, None)
        with responses.RequestsMock() as google:
            google.post(GOOGLE_TOKEN_URL, status=500)
            response = client.get(
                reverse("google_callback"), {"code": "code", "state": state}
            )

        assert_rejected(client, response, FAILED_MESSAGE)
