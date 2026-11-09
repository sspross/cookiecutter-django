from pathlib import Path
from typing import Any

import django_stubs_ext
import environ

from core.observability import DEFAULT_ENVIRONMENT as SENTRY_DEFAULT_ENVIRONMENT

django_stubs_ext.monkeypatch()

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    DJANGO_VITE_DEV_MODE=(bool, None),
    SENTRY_DSN=(str, ""),
    SENTRY_ENVIRONMENT=(str, SENTRY_DEFAULT_ENVIRONMENT),
    GOOGLE_OAUTH_CLIENT_ID=(str, ""),
    GOOGLE_OAUTH_CLIENT_SECRET=(str, ""),
    SSO_ALLOWED_DOMAINS=(list, []),
    SSO_ALLOWED_EMAILS=(list, ["{{ cookiecutter.author_email }}"]),
    SSO_SUPERUSER_EMAILS=(list, ["{{ cookiecutter.author_email }}"]),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

environ.Env.read_env(Path(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

PROJECT_NAME = "{{ cookiecutter.project_name }}"

# Only safe while the proxy in front of the app strips a client-supplied
# X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_vite",
    "django_rq",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "users",
    "api_keys",
    "core",
]

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    # First, so a response another middleware produces is correlated too.
    "core.request_context.RequestContextMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context.site",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": env.db(),
}

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]


def google_providers(client_id: str, secret: str) -> dict[str, Any]:
    if not client_id:
        return {}
    return {
        "google": {
            "APP": {"client_id": client_id, "secret": secret},
            "SCOPE": ["openid", "email", "profile"],
            "OAUTH_PKCE_ENABLED": True,
        },
    }


SOCIALACCOUNT_PROVIDERS = google_providers(
    env("GOOGLE_OAUTH_CLIENT_ID"), env("GOOGLE_OAUTH_CLIENT_SECRET")
)
ACCOUNT_ADAPTER = "users.sso.SsoAccountAdapter"
SOCIALACCOUNT_ADAPTER = "users.sso.SsoSocialAccountAdapter"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
# The allowlist rejects unverified emails, so allauth never has to send mail.
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SSO_ALLOWED_DOMAINS = env("SSO_ALLOWED_DOMAINS")
SSO_ALLOWED_EMAILS = env("SSO_ALLOWED_EMAILS")
SSO_SUPERUSER_EMAILS = env("SSO_SUPERUSER_EMAILS")

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa: E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

MEDIA_ROOT = env.str("MEDIA_ROOT", default=str(BASE_DIR / "media"))
MEDIA_URL = env.str("MEDIA_URL", default="media/")

# Keep `static_url_prefix` in sync with `base` in core/frontend/vite.config.mjs.
_vite_dev_mode = env("DJANGO_VITE_DEV_MODE")
DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG if _vite_dev_mode is None else _vite_dev_mode,
        "static_url_prefix": "dist/js",
    },
}

REDIS_URL = env("REDIS_URL")
RQ_QUEUES = {
    "default": {
        "URL": REDIS_URL,
        "DEFAULT_TIMEOUT": 360,
    },
}

# Shares the RQ database, so cache.clear() drops queued jobs. See docs/OPERATIONS.md.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "{{ cookiecutter.project_slug }}",
    },
}

# Fails safe: only the literal "false" turns enforcement off, a typo keeps it on.
HTTPS_ENFORCED = env.str("HTTPS_ENFORCED", default="true").lower() != "false"

if not DEBUG and HTTPS_ENFORCED:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

# W005 and W021 flag the two HSTS scope settings above, which are deliberate.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": (
                "%(asctime)s %(levelname)s "
                "[%(request_id)s %(request_source)s] %(name)s %(message)s"
            ),
        },
    },
    "filters": {
        "request_context": {
            "()": "core.request_context.RequestContextFilter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
            "filters": ["request_context"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    # A level-only entry still clears the handlers Django's logging config put on
    # that logger, leaving root as the one place a record is printed.
    "loggers": {
        "core": {"level": "INFO"},
        "api_keys": {"level": "INFO"},
        "users": {"level": "INFO"},
        "django": {"level": "WARNING"},
        "django.request": {"level": "ERROR"},
        "rq": {"level": "WARNING"},
    },
}

SENTRY_DSN = env("SENTRY_DSN")
SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT")
