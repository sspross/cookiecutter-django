import logging
from dataclasses import dataclass
from typing import Any

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.base import AuthError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.base_user import AbstractBaseUser
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import resolve_url

logger = logging.getLogger(__name__)

NOT_ALLOWED_MESSAGE = "This Google account is not allowed to sign in."
CANCELLED_MESSAGE = "Google sign-in was cancelled."
FAILED_MESSAGE = "Google sign-in failed. Please try again."


@dataclass(frozen=True)
class GoogleIdentity:
    email: str
    email_verified: bool
    hosted_domain: str

    @classmethod
    def from_claims(cls, claims: dict[str, Any]) -> "GoogleIdentity":
        return cls(
            email=str(claims.get("email") or "").lower(),
            email_verified=claims.get("email_verified") is True,
            hosted_domain=str(claims.get("hd") or "").lower(),
        )


def rejection_reason(identity: GoogleIdentity) -> str | None:
    """The SSO allowlist. `None` means the identity may sign in.

    A domain matches on Google's `hd` claim only, never on the email suffix: a
    private Google account can carry a verified `name@company.com` address.
    """
    if not identity.email_verified:
        return "email not verified by Google"
    if identity.email == settings.SSO_SUPERUSER_EMAIL.lower():
        return None
    if identity.email in _lowercased(settings.SSO_ALLOWED_EMAILS):
        return None
    if identity.hosted_domain in _lowercased(settings.SSO_ALLOWED_DOMAINS):
        return None
    return "not on the SSO allowlist"


def _lowercased(values: list[str]) -> set[str]:
    return {value.strip().lower() for value in values if value.strip()}


def _back_to_login(request: HttpRequest, message: str) -> HttpResponseRedirect:
    messages.error(request, message)
    return HttpResponseRedirect(resolve_url(settings.LOGIN_URL))


class SsoSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request: HttpRequest, sociallogin: SocialLogin) -> None:
        identity = GoogleIdentity.from_claims(sociallogin.account.extra_data)
        reason = rejection_reason(identity)
        user = sociallogin.user
        # allauth answers an inactive user with its own page, not mounted here.
        if reason is None and sociallogin.is_existing and not user.is_active:
            reason = "user is inactive"
        if reason is not None:
            logger.info("Rejected Google login for %s: %s", identity.email, reason)
            raise ImmediateHttpResponse(_back_to_login(request, NOT_ALLOWED_MESSAGE))

    def on_authentication_error(
        self,
        request: HttpRequest,
        provider: Any,
        error: str | None = None,
        exception: Exception | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> None:
        logger.info("Google login did not complete: %s %r", error, exception)
        message = CANCELLED_MESSAGE if error == AuthError.CANCELLED else FAILED_MESSAGE
        raise ImmediateHttpResponse(_back_to_login(request, message))

    def populate_user(
        self, request: HttpRequest, sociallogin: SocialLogin, data: dict[str, Any]
    ) -> AbstractBaseUser:
        user = super().populate_user(request, sociallogin, data)
        # allauth replaces a taken username with a generated one.
        user.username = user.email.partition("@")[0]
        return user

    def save_user(
        self, request: HttpRequest, sociallogin: SocialLogin, form: Any = None
    ) -> AbstractBaseUser:
        user = sociallogin.user
        if user.email.lower() == settings.SSO_SUPERUSER_EMAIL.lower():
            user.is_superuser = True
            user.is_staff = True
        return super().save_user(request, sociallogin, form)
