"""Selector tests for `example.selectors`.

Selectors are the read-only query layer. These tests exercise:
- the queryset shape returned by `list_tags` against seed data,
- filter combinations consumed via `TagFilters`,
- pagination edges (sliced via `[offset:offset+limit]` to mirror the
  `LimitOffsetPagination` slicing the API layer applies).
"""

import pytest

from example import selectors
from example.filters import TagFilters
from example.tests.factories import TagFactory


@pytest.mark.django_db
class TestListTags:
    def test_returns_all_tags_ordered_by_name(self):
        TagFactory(name="Charlie", slug="charlie")
        TagFactory(name="Alpha", slug="alpha")
        TagFactory(name="Bravo", slug="bravo")

        tags = list(selectors.list_tags())

        assert [t.name for t in tags] == ["Alpha", "Bravo", "Charlie"]

    def test_filters_by_name_icontains(self):
        TagFactory(name="Backend", slug="backend")
        TagFactory(name="Frontend", slug="frontend")
        TagFactory(name="Database", slug="database")

        filters = TagFilters(name="end")
        tags = list(selectors.list_tags(filters=filters))

        names = {t.name for t in tags}
        assert names == {"Backend", "Frontend"}

    def test_filters_by_slug_icontains(self):
        TagFactory(name="A", slug="alpha-one")
        TagFactory(name="B", slug="beta-two")

        filters = TagFilters(slug="alpha")
        tags = list(selectors.list_tags(filters=filters))

        assert [t.slug for t in tags] == ["alpha-one"]

    def test_filters_combine_as_and(self):
        TagFactory(name="Backend", slug="backend")
        TagFactory(name="Frontend", slug="frontend")
        TagFactory(name="Backstage", slug="back-stage")

        filters = TagFilters(name="back", slug="back-")
        tags = list(selectors.list_tags(filters=filters))

        assert [t.name for t in tags] == ["Backstage"]

    def test_no_filters_returns_full_queryset(self):
        TagFactory.create_batch(5)
        assert selectors.list_tags().count() == 5

    def test_pagination_edge_offset_beyond_total_returns_empty(self):
        TagFactory.create_batch(3)
        qs = selectors.list_tags()
        page = list(qs[10:20])
        assert page == []

    def test_pagination_edge_first_page(self):
        for i in range(5):
            TagFactory(name=f"Z{i:02d}", slug=f"z-{i:02d}")
        qs = selectors.list_tags()
        page = list(qs[0:2])
        assert [t.name for t in page] == ["Z00", "Z01"]


@pytest.mark.django_db
class TestGetTag:
    def test_returns_tag_by_pk(self):
        tag = TagFactory()
        assert selectors.get_tag(tag_id=tag.pk) == tag

    def test_raises_does_not_exist_for_unknown_pk(self):
        from example.models import Tag

        with pytest.raises(Tag.DoesNotExist):
            selectors.get_tag(tag_id=9999)
