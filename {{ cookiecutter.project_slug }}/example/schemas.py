"""Wire-format schemas for the `example` app.

Schemas live separately from `api` so the api module stays a thin
deserialize/dispatch/serialize layer. In/Out shapes are also reused by the
service tests when they want to assert payload shape without going through
the HTTP layer.
"""

from datetime import datetime

from ninja import Schema


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
