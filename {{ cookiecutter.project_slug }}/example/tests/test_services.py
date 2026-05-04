"""Service tests for `example.services`.

Services are the write layer; they call `full_clean` before save and
return the persisted instance. These tests assert state changes and that
invalid input raises Django's `ValidationError` (which the project-wide
Ninja handler maps to a 422).
"""

import pytest
from django.core.exceptions import ValidationError

from example import services
from example.models import Tag
from example.tests.factories import TagFactory


@pytest.mark.django_db
class TestCreateTag:
    def test_persists_tag_and_returns_instance(self):
        tag = services.create_tag(name="Alpha", slug="alpha")
        assert tag.pk is not None
        assert Tag.objects.filter(pk=tag.pk).exists()
        assert tag.name == "Alpha"
        assert tag.slug == "alpha"

    def test_full_clean_rejects_blank_name(self):
        with pytest.raises(ValidationError):
            services.create_tag(name="", slug="alpha")

    def test_full_clean_rejects_invalid_slug(self):
        with pytest.raises(ValidationError):
            services.create_tag(name="Alpha", slug="not a slug!")

    def test_unique_constraint_rejects_duplicate_name(self):
        services.create_tag(name="Alpha", slug="alpha-1")
        with pytest.raises(ValidationError):
            services.create_tag(name="Alpha", slug="alpha-2")


@pytest.mark.django_db
class TestUpdateTag:
    def test_changes_fields_and_persists(self):
        tag = TagFactory(name="Old", slug="old")
        updated = services.update_tag(tag=tag, name="New", slug="new")
        updated.refresh_from_db()
        assert updated.name == "New"
        assert updated.slug == "new"

    def test_partial_update_leaves_unspecified_fields(self):
        tag = TagFactory(name="Stay", slug="stay-original")
        updated = services.update_tag(tag=tag, slug="stay-new")
        updated.refresh_from_db()
        assert updated.name == "Stay"
        assert updated.slug == "stay-new"

    def test_full_clean_rejects_invalid_update(self):
        tag = TagFactory()
        with pytest.raises(ValidationError):
            services.update_tag(tag=tag, slug="not a slug!")


@pytest.mark.django_db
class TestDeleteTag:
    def test_removes_tag_from_db(self):
        tag = TagFactory()
        services.delete_tag(tag=tag)
        assert not Tag.objects.filter(pk=tag.pk).exists()
