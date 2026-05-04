"""Typed query-param filters for the `example` app.

Selectors consume validated `FilterSchema` objects rather than raw dicts.
The API layer wires these up via `Query[...]` so the parameters appear
typed in the OpenAPI document and flow through to the SPA's typed client.
"""

from typing import Annotated

from ninja import FilterLookup, FilterSchema


class TagFilters(FilterSchema):
    name: Annotated[str | None, FilterLookup(q="name__icontains")] = None
    slug: Annotated[str | None, FilterLookup(q="slug__icontains")] = None
