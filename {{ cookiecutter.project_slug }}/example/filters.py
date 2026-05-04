"""Typed query-param filters for the `example` app.

Selectors consume validated `FilterSchema` objects rather than raw dicts.
The API layer wires these up via `Query[...]` so the parameters appear
typed in the OpenAPI document and flow through to the SPA's typed client.
"""

from typing import Annotated, Literal

from ninja import FilterLookup, FilterSchema


class TagFilters(FilterSchema):
    name: Annotated[str | None, FilterLookup(q="name__icontains")] = None
    slug: Annotated[str | None, FilterLookup(q="slug__icontains")] = None


class ProjectFilters(FilterSchema):
    title: Annotated[str | None, FilterLookup(q="title__icontains")] = None
    status: Annotated[
        Literal["draft", "active", "archived"] | None, FilterLookup(q="status")
    ] = None
    # Tag filter is a single tag id; selectors compose the lookup so a
    # project that has the tag is included.
    tag: Annotated[int | None, FilterLookup(q="tags__id")] = None
