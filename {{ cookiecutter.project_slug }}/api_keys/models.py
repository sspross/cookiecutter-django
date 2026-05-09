from django.conf import settings
from django.db import models


class UserApiKey(models.Model):
    """A bearer credential for the headless API path.

    The raw token (`{{ cookiecutter.project_slug }}_live_<urlsafe>`) is shown
    to the user exactly once on creation. Only `sha256(raw_token)` is
    persisted; the database never holds the live credential. `prefix` stores
    the first ~12 characters of the raw token so the admin UI can identify a
    key without revealing it.

    Soft-delete vocabulary: `revoked_at` follows the visible-but-marked
    convention. Revoked rows stay queryable in the admin and in the user's
    own list (so they can audit "did I revoke that key?"), but `verify()`
    rejects them. Contrast with `deleted_at`, which would mean
    "hide from users entirely."
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    name = models.CharField(max_length=128)
    prefix = models.CharField(max_length=16)
    hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "User API key"
        verbose_name_plural = "User API keys"

    def __str__(self) -> str:
        suffix = " (revoked)" if self.revoked_at else ""
        return f"{self.user}: {self.name} [{self.prefix}…]{suffix}"

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
