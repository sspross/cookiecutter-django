"""Service tests for `example.services` (Project)."""

import pytest
from django.core.exceptions import ValidationError

from example import services
from example.tests.factories import ProjectFactory, TagFactory


@pytest.mark.django_db
class TestCreateProject:
    def test_persists_project_and_returns_instance(self):
        project = services.create_project(
            title="A", description="d", status="draft"
        )
        assert project.pk is not None
        assert project.title == "A"
        assert project.status == "draft"
        assert list(project.tags.all()) == []

    def test_assigns_tags_after_save(self):
        backend = TagFactory(name="Backend", slug="backend")
        frontend = TagFactory(name="Frontend", slug="frontend")

        project = services.create_project(
            title="A",
            tag_ids=[backend.pk, frontend.pk],
        )

        assert {t.pk for t in project.tags.all()} == {backend.pk, frontend.pk}

    def test_rejects_unknown_tag_ids(self):
        backend = TagFactory(name="Backend", slug="backend")
        with pytest.raises(ValidationError) as exc:
            services.create_project(
                title="A", tag_ids=[backend.pk, 999_999]
            )
        assert "tag_ids" in exc.value.message_dict

    def test_full_clean_rejects_invalid_status(self):
        with pytest.raises(ValidationError):
            services.create_project(title="A", status="not-a-status")

    def test_full_clean_rejects_blank_title(self):
        with pytest.raises(ValidationError):
            services.create_project(title="")


@pytest.mark.django_db
class TestUpdateProject:
    def test_partial_update_does_not_touch_tags(self):
        backend = TagFactory(name="Backend", slug="backend")
        project = ProjectFactory(title="Old", tags=[backend])

        updated = services.update_project(project=project, title="New")

        updated.refresh_from_db()
        assert updated.title == "New"
        assert {t.pk for t in updated.tags.all()} == {backend.pk}

    def test_replaces_tags_when_tag_ids_provided(self):
        backend = TagFactory(name="Backend", slug="backend")
        frontend = TagFactory(name="Frontend", slug="frontend")
        infra = TagFactory(name="Infra", slug="infra")
        project = ProjectFactory(title="P", tags=[backend, frontend])

        updated = services.update_project(
            project=project, tag_ids=[infra.pk]
        )

        assert {t.pk for t in updated.tags.all()} == {infra.pk}

    def test_clears_tags_when_empty_list_provided(self):
        backend = TagFactory(name="Backend", slug="backend")
        project = ProjectFactory(title="P", tags=[backend])

        updated = services.update_project(project=project, tag_ids=[])

        assert list(updated.tags.all()) == []


@pytest.mark.django_db
class TestDeleteProject:
    def test_removes_project(self):
        from example.models import Project

        project = ProjectFactory()
        services.delete_project(project=project)
        assert not Project.objects.filter(pk=project.pk).exists()
