from typing import Any

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    def save(self, *args: Any, **kwargs: Any) -> None:
        # allauth links a Google login to User.email by exact match on the
        # lowercased address, and normalize_email only lowercases the domain.
        self.email = self.email.lower()
        super().save(*args, **kwargs)
