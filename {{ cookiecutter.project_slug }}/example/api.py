"""HTTP edge for the `example` app.

The api module exports a Ninja `Router` and stays thin: deserialize,
dispatch to selector or service, serialize. All read-side logic lives in
`selectors`; all write-side logic lives in `services`. Validation errors
from `full_clean` are translated to 422 by the global handler in
`core.api`.

CSRF: GETs are unprotected (idempotent reads). Mutations are wrapped with
`csrf_protect_route` so Django's CSRF check runs on POST/PATCH/DELETE.
"""

from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.pagination import LimitOffsetPagination, paginate
from ninja.responses import Status

from core.csrf import csrf_protect_route
from example import selectors, services
from example.filters import TagFilters
from example.models import Tag
from example.schemas import TagIn, TagOut, TagPatch

router = Router()


@router.get("/tags", response=list[TagOut], tags=["tags"])
@paginate(LimitOffsetPagination)
def list_tags(request, filters: Query[TagFilters]):
    return selectors.list_tags(filters=filters)


@router.get("/tags/{tag_id}", response=TagOut, tags=["tags"])
def get_tag(request, tag_id: int) -> Tag:
    return get_object_or_404(Tag, pk=tag_id)


@router.post("/tags", response={201: TagOut}, tags=["tags"])
@csrf_protect_route
def create_tag(request, payload: TagIn):
    tag = services.create_tag(**payload.dict())
    return Status(201, tag)


@router.patch("/tags/{tag_id}", response=TagOut, tags=["tags"])
@csrf_protect_route
def update_tag(request, tag_id: int, payload: TagPatch) -> Tag:
    tag = get_object_or_404(Tag, pk=tag_id)
    return services.update_tag(tag=tag, **payload.dict(exclude_unset=True))


@router.delete("/tags/{tag_id}", response={204: None}, tags=["tags"])
@csrf_protect_route
def delete_tag(request, tag_id: int):
    tag = get_object_or_404(Tag, pk=tag_id)
    services.delete_tag(tag=tag)
    return Status(204, None)
