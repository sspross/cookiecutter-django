from typing import Any

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = self.email.lower()
        super().save(*args, **kwargs)
