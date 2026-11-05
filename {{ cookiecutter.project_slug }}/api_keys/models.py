from django.conf import settings
from django.db import models


class UserApiKey(models.Model):
    NAME_MAX_LENGTH = 128

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    name = models.CharField(max_length=NAME_MAX_LENGTH)
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
