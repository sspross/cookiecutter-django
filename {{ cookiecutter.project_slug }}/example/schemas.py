"""Wire-format schemas for the `example` app.

Schemas live separately from `api` so the api module stays a thin
deserialize/dispatch/serialize layer. In/Out shapes are also reused by the
service tests when they want to assert payload shape without going through
the HTTP layer.
"""

from datetime import datetime
from typing import Literal

from ninja import Schema

ProjectStatus = Literal["draft", "active", "archived"]


class TagOut(Schema):
    id: int
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class TagIn(Schema):
    name: str
    slug: str


class TagPatch(Schema):
    name: str | None = None
    slug: str | None = None


class ProjectOut(Schema):
    id: int
    title: str
    description: str
    status: ProjectStatus
    tags: list[TagOut]
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_tags(obj):
        # `obj.tags` is a related manager; the serializer needs the list.
        return list(obj.tags.all())


class ProjectIn(Schema):
    title: str
    description: str = ""
    status: ProjectStatus = "draft"
    tag_ids: list[int] = []


class ProjectPatch(Schema):
    title: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None
    tag_ids: list[int] | None = None
