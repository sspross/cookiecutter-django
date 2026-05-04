"""Filter tests for `example.filters`.

`TagFilters` is exercised here in isolation — without going through the
selector — so the FilterSchema's Q-expression construction is verified
against the queryset directly.
"""

import pytest

from example.filters import TagFilters
from example.models import Tag
from example.tests.factories import TagFactory


@pytest.mark.django_db
class TestTagFilters:
    def test_empty_filter_matches_everything(self):
        TagFactory.create_batch(3)
        filters = TagFilters()
        assert filters.filter(Tag.objects.all()).count() == 3

    def test_name_filter_is_case_insensitive(self):
        TagFactory(name="Backend", slug="backend")
        TagFactory(name="frontend", slug="frontend")
        filters = TagFilters(name="BACK")
        result = list(filters.filter(Tag.objects.all()))
        assert [t.name for t in result] == ["Backend"]

    def test_slug_filter_is_substring(self):
        TagFactory(name="A", slug="alpha-1")
        TagFactory(name="B", slug="beta-1")
        TagFactory(name="C", slug="alpha-2")
        filters = TagFilters(slug="alpha")
        result = list(filters.filter(Tag.objects.all()).order_by("slug"))
        assert [t.slug for t in result] == ["alpha-1", "alpha-2"]
