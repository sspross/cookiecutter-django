from typing import Any

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    def save(self, *args: Any, **kwargs: Any) -> None:
        # Google login links by exact, lowercased email; see ADR-0009.
        self.email = self.email.lower()
        super().save(*args, **kwargs)
