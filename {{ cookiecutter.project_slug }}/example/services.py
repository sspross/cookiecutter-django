"""Write-side business operations for the `example` app.

Services accept kwargs only, call `full_clean()` before save, and return
the persisted instance. Validation errors raised by `full_clean` are
caught by the project-wide Ninja exception handler in `core.api` and
mapped to a 422 response that the SPA's RHF helper consumes.
"""

from collections.abc import Iterable

from django.core.exceptions import ValidationError

from example.models import Project, Tag


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


def _resolve_tags(tag_ids: Iterable[int]) -> list[Tag]:
    """Look up tags by id, raising `ValidationError` on any unknown id.

    The handler in `core.api` maps this to a 422 response with the
    invalid ids in the field-specific error, mirroring how Django's
    `full_clean` errors flow.
    """
    ids = list(tag_ids)
    if not ids:
        return []
    found = list(Tag.objects.filter(pk__in=ids))
    if len(found) != len(set(ids)):
        missing = sorted(set(ids) - {t.pk for t in found})
        raise ValidationError({"tag_ids": [f"Unknown tag ids: {missing}"]})
    return found


def create_project(
    *,
    title: str,
    description: str = "",
    status: str = "draft",
    tag_ids: Iterable[int] = (),
) -> Project:
    tags = _resolve_tags(tag_ids)
    project = Project(title=title, description=description, status=status)
    project.full_clean()
    project.save()
    if tags:
        project.tags.set(tags)
    return project


def update_project(
    *,
    project: Project,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    tag_ids: Iterable[int] | None = None,
) -> Project:
    if title is not None:
        project.title = title
    if description is not None:
        project.description = description
    if status is not None:
        project.status = status
    project.full_clean()
    project.save()
    if tag_ids is not None:
        project.tags.set(_resolve_tags(tag_ids))
    return project


def delete_project(*, project: Project) -> None:
    project.delete()
