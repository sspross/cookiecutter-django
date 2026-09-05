from django.apps import AppConfig
from django.conf import settings

from core.observability import init_sentry


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    label = "core"

    def ready(self) -> None:
        init_sentry(settings.SENTRY_DSN, settings.SENTRY_ENVIRONMENT)
