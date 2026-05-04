"""Filter tests for `example.filters.ProjectFilters` in isolation."""

import pytest

from example.filters import ProjectFilters
from example.models import Project
from example.tests.factories import ProjectFactory, TagFactory


@pytest.mark.django_db
class TestProjectFilters:
    def test_empty_filter_matches_everything(self):
        ProjectFactory.create_batch(3)
        qs = ProjectFilters().filter(Project.objects.all())
        assert qs.count() == 3

    def test_status_filter_is_exact_match(self):
        ProjectFactory(title="A", status="draft")
        ProjectFactory(title="B", status="active")
        ProjectFactory(title="C", status="archived")
        qs = ProjectFilters(status="active").filter(Project.objects.all())
        assert [p.title for p in qs] == ["B"]

    def test_tag_filter_resolves_through_m2m(self):
        backend = TagFactory(name="Backend", slug="backend")
        ProjectFactory(title="A", tags=[backend])
        ProjectFactory(title="B")
        qs = (
            ProjectFilters(tag=backend.pk)
            .filter(Project.objects.all())
            .distinct()
        )
        assert [p.title for p in qs] == ["A"]
