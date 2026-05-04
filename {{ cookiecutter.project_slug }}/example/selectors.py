"""Read-side query layer for the `example` app.

Selectors are read-only, accept kwargs only, and consume validated
`FilterSchema` instances rather than raw dicts. They never write to the
database — that's services' job.
"""

from django.db.models import QuerySet

from example.filters import TagFilters
from example.models import Tag


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
