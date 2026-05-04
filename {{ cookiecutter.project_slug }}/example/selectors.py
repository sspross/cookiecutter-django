"""Read-side query layer for the `example` app.

Selectors are read-only, accept kwargs only, and consume validated
`FilterSchema` instances rather than raw dicts. They never write to the
database — that's services' job.
"""

from django.db.models import QuerySet

from example.filters import ProjectFilters, TagFilters, TaskFilters
from example.models import Project, Tag, Task


def list_tags(*, filters: TagFilters | None = None) -> QuerySet[Tag]:
    """Return the queryset of tags, narrowed by the given filter schema."""
    qs = Tag.objects.all()
    if filters is not None:
        qs = filters.filter(qs)
    return qs


def get_tag(*, tag_id: int) -> Tag:
    """Fetch a single tag by primary key.

    Raises `Tag.DoesNotExist` if no tag matches; callers map that to 404.
    """
    return Tag.objects.get(pk=tag_id)


def list_projects(*, filters: ProjectFilters | None = None) -> QuerySet[Project]:
    """Return the queryset of projects with tags prefetched.

    Tag filtering goes through `tags__id`, which would otherwise duplicate
    rows if a project had multiple matching tags. `distinct()` collapses
    those back to one row per project.
    """
    qs = Project.objects.all().prefetch_related("tags")
    if filters is not None:
        qs = filters.filter(qs)
        if filters.tag is not None:
            qs = qs.distinct()
    return qs


def get_project(*, project_id: int) -> Project:
    return Project.objects.prefetch_related("tags").get(pk=project_id)


def list_tasks(*, filters: TaskFilters | None = None) -> QuerySet[Task]:
    qs = Task.objects.all()
    if filters is not None:
        qs = filters.filter(qs)
    return qs


def get_task(*, task_id: int) -> Task:
    return Task.objects.get(pk=task_id)
