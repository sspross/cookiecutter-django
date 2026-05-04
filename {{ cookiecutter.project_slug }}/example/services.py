"""Write-side business operations for the `example` app.

Services accept kwargs only, call `full_clean()` before save, and return
the persisted instance. Validation errors raised by `full_clean` are
caught by the project-wide Ninja exception handler in `core.api` and
mapped to a 422 response that the SPA's RHF helper consumes.
"""

from example.models import Tag


def create_tag(*, name: str, slug: str) -> Tag:
    tag = Tag(name=name, slug=slug)
    tag.full_clean()
    tag.save()
    return tag


def update_tag(
    *,
    tag: Tag,
    name: str | None = None,
    slug: str | None = None,
) -> Tag:
    if name is not None:
        tag.name = name
    if slug is not None:
        tag.slug = slug
    tag.full_clean()
    tag.save()
    return tag


def delete_tag(*, tag: Tag) -> None:
    tag.delete()
