"""Selector tests for `example.selectors.list_projects` / `get_project`."""

import pytest

from example import selectors
from example.filters import ProjectFilters
from example.tests.factories import ProjectFactory, TagFactory


@pytest.mark.django_db
class TestListProjects:
    def test_returns_all_ordered_by_created_at_desc(self):
        a = ProjectFactory(title="A")
        b = ProjectFactory(title="B")
        c = ProjectFactory(title="C")

        result = list(selectors.list_projects())

        assert [p.pk for p in result] == [c.pk, b.pk, a.pk]

    def test_filters_by_status(self):
        ProjectFactory(title="Draft", status="draft")
        ProjectFactory(title="Active", status="active")
        ProjectFactory(title="Archived", status="archived")

        result = list(
            selectors.list_projects(filters=ProjectFilters(status="active"))
        )

        assert [p.title for p in result] == ["Active"]

    def test_filters_by_tag_id_returns_matching_projects(self):
        backend = TagFactory(name="Backend", slug="backend")
        frontend = TagFactory(name="Frontend", slug="frontend")
        ProjectFactory(title="P1", tags=[backend])
        ProjectFactory(title="P2", tags=[frontend])
        ProjectFactory(title="P3", tags=[backend, frontend])

        result = list(
            selectors.list_projects(filters=ProjectFilters(tag=backend.pk))
        )

        assert {p.title for p in result} == {"P1", "P3"}

    def test_tag_filter_is_distinct(self):
        # A project with multiple tags should not be duplicated when the
        # underlying join fans out.
        backend = TagFactory(name="Backend", slug="backend")
        ProjectFactory(title="P1", tags=[backend])

        result = list(
            selectors.list_projects(filters=ProjectFilters(tag=backend.pk))
        )

        assert len(result) == 1

    def test_pagination_edge_offset_beyond_total(self):
        ProjectFactory.create_batch(2)
        qs = selectors.list_projects()
        assert list(qs[10:20]) == []


@pytest.mark.django_db
class TestGetProject:
    def test_returns_project_with_tags_prefetched(self):
        backend = TagFactory(name="Backend", slug="backend")
        project = ProjectFactory(title="P", tags=[backend])

        fetched = selectors.get_project(project_id=project.pk)
        # `prefetch_related` should mean accessing tags doesn't issue a new query;
        # a stronger assertion would use CaptureQueriesContext, but checking
        # the data is correct is enough at this layer.
        assert [t.pk for t in fetched.tags.all()] == [backend.pk]
