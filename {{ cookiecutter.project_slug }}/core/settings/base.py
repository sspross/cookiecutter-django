from pathlib import Path

import environ

from core.observability import DEFAULT_ENVIRONMENT as SENTRY_DEFAULT_ENVIRONMENT

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    DJANGO_VITE_DEV_MODE=(bool, None),
    SENTRY_DSN=(str, ""),
    SENTRY_ENVIRONMENT=(str, SENTRY_DEFAULT_ENVIRONMENT),
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

environ.Env.read_env(Path(BASE_DIR, ".env"))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

PROJECT_NAME = "{{ cookiecutter.project_name }}"

# Only safe while the proxy in front of the app strips a client-supplied
# X-Forwarded-Proto. Appliku's does; a self-run reverse proxy has to be
# configured to.
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
    "users",
    "api_keys",
    "core",
]

AUTH_USER_MODEL = "users.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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

MEDIA_ROOT = env.str("MEDIA_ROOT", default=str(BASE_DIR / "media"))  # type: ignore
MEDIA_URL = env.str("MEDIA_URL", default="media/")  # type: ignore

# Keep `static_url_prefix` in sync with vite.config.mjs's `base`.
# DJANGO_VITE_DEV_MODE decouples dev_mode from DEBUG, so `runserver` can serve
# the built manifest without flipping DEBUG off.
_vite_dev_mode = env("DJANGO_VITE_DEV_MODE")
DJANGO_VITE = {
    "default": {
        "dev_mode": DEBUG if _vite_dev_mode is None else _vite_dev_mode,
        "static_url_prefix": "dist/js",
    },
}

# Redis is required at enqueue time for Job persistence even when a queue runs
# ASYNC=False (as tests do). See ADR-0003.
REDIS_URL = env("REDIS_URL")
RQ_QUEUES = {
    "default": {
        "URL": REDIS_URL,
        "DEFAULT_TIMEOUT": 360,
    },
}

# Shared across gunicorn workers, so throttle counters hold under concurrency.
# Shares the RQ database, and RedisCache.clear() is FLUSHDB: clearing the whole
# cache would drop queued jobs with it.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "{{ cookiecutter.project_slug }}",
    },
}

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

# W005 and W021 flag the two HSTS scope settings above, which are deliberate.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "format": "{levelname} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    # Level only, no "handlers" key: that drops the handlers Django's own
    # logging config puts on these loggers, leaving root as the one place a
    # record is printed. See docs/OPERATIONS.md, "Logs and monitoring".
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
