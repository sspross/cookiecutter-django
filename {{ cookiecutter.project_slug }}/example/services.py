"""Write-side business operations for the `example` app.

Services accept kwargs only, call `full_clean()` before save, and return
the persisted instance. Validation errors raised by `full_clean` are
caught by the project-wide Ninja exception handler in `core.api` and
mapped to a 422 response that the SPA's RHF helper consumes.
"""

from collections.abc import Iterable
from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from example.models import Project, Tag, Task


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


def create_task(
    *,
    project_id: int,
    title: str,
    description: str = "",
    status: str = "todo",
    priority: str = "medium",
    due_date: date | None = None,
    completed_at: datetime | None = None,
) -> Task:
    project = get_object_or_404(Project, pk=project_id)
    task = Task(
        project=project,
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
        completed_at=completed_at,
    )
    task.full_clean()
    task.save()
    return task


_TASK_UPDATABLE = (
    "title",
    "description",
    "status",
    "priority",
    "due_date",
    "completed_at",
)


def update_task(*, task: Task, **fields) -> Task:
    """Apply a partial update.

    Only fields present in `fields` are touched. `due_date` and
    `completed_at` accept `None` as a real value (clear the field), which
    is why this signature keys off "is the field present at all" rather
    than "is the value not None". Callers (the API layer) build `fields`
    from `payload.dict(exclude_unset=True)` so unset fields are skipped.
    """
    unknown = set(fields) - set(_TASK_UPDATABLE)
    if unknown:
        raise TypeError(f"update_task got unexpected fields: {sorted(unknown)}")
    for name, value in fields.items():
        setattr(task, name, value)
    task.full_clean()
    task.save()
    return task


def delete_task(*, task: Task) -> None:
    task.delete()
