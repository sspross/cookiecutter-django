"""Domain models for the `example` app.

The `Tag` resource is the first slice that establishes the layering pattern
the rest of the example app follows: models stay free of business logic,
selectors handle reads, services handle writes (and call `full_clean` before
save), and the API layer stays thin.
"""

from django.db import models


class Tag(models.Model):
    """A short label that can be attached to other resources.

    `name` is the human-facing label; `slug` is the URL-safe form used in
    filters and search params. Both are unique because the demo's filter UX
    relies on a tag being addressable by either.
    """

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
