"""API tests for `example.api`.

These exercise the HTTP layer: status codes, payload shape, the CSRF
contract on mutations, and the 422 shape produced by the project-wide
Django `ValidationError` handler.
"""

import pytest

from example.models import Tag
from example.tests.factories import TagFactory


@pytest.mark.django_db
class TestListTags:
    def test_returns_paginated_envelope(self, client):
        TagFactory(name="Alpha", slug="alpha")
        TagFactory(name="Bravo", slug="bravo")

        response = client.get("/api/example/tags")

        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "count" in body
        assert body["count"] == 2
        assert len(body["items"]) == 2
        item = body["items"][0]
        assert {"id", "name", "slug", "created_at", "updated_at"} <= set(item.keys())

    def test_filters_by_name_query_param(self, client):
        TagFactory(name="Backend", slug="backend")
        TagFactory(name="Frontend", slug="frontend")

        response = client.get("/api/example/tags?name=back")

        assert response.status_code == 200
        body = response.json()
        names = {item["name"] for item in body["items"]}
        assert names == {"Backend"}

    def test_pagination_limit_and_offset(self, client):
        for i in range(5):
            TagFactory(name=f"Tag {i:02d}", slug=f"tag-{i:02d}")

        response = client.get("/api/example/tags?limit=2&offset=2")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 5
        assert len(body["items"]) == 2
        assert [item["name"] for item in body["items"]] == ["Tag 02", "Tag 03"]


@pytest.mark.django_db
class TestGetTag:
    def test_returns_single_tag(self, client):
        tag = TagFactory(name="Solo", slug="solo")

        response = client.get(f"/api/example/tags/{tag.pk}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == tag.pk
        assert body["name"] == "Solo"
        assert body["slug"] == "solo"

    def test_returns_404_for_unknown_id(self, client):
        response = client.get("/api/example/tags/9999")
        assert response.status_code == 404


@pytest.mark.django_db
class TestCreateTag:
    def test_rejects_post_without_csrf(self, client):
        # The default Django test client is CSRF-exempt; opt in to the
        # CSRF check by enforcing it on the client.
        client.handler.enforce_csrf_checks = True
        response = client.post(
            "/api/example/tags",
            data={"name": "Alpha", "slug": "alpha"},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert not Tag.objects.filter(slug="alpha").exists()

    def test_creates_tag_with_csrf_header(self, client):
        # Prime the csrftoken cookie.
        client.get("/api/config")
        client.handler.enforce_csrf_checks = True
        token = client.cookies["csrftoken"].value

        response = client.post(
            "/api/example/tags",
            data={"name": "Alpha", "slug": "alpha"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Alpha"
        assert body["slug"] == "alpha"
        assert Tag.objects.filter(slug="alpha").exists()

    def test_invalid_payload_returns_pydantic_422(self, client):
        client.get("/api/config")
        client.handler.enforce_csrf_checks = True
        token = client.cookies["csrftoken"].value

        # `name` is required but missing — Pydantic catches it first.
        response = client.post(
            "/api/example/tags",
            data={"slug": "alpha"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 422
        body = response.json()
        assert "detail" in body
        assert isinstance(body["detail"], list)
        first = body["detail"][0]
        assert "loc" in first and "msg" in first

    def test_invalid_slug_returns_django_validation_422(self, client):
        client.get("/api/config")
        client.handler.enforce_csrf_checks = True
        token = client.cookies["csrftoken"].value

        # Pydantic accepts the string; `full_clean` rejects it.
        response = client.post(
            "/api/example/tags",
            data={"name": "Alpha", "slug": "not a slug!"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 422
        body = response.json()
        assert "detail" in body
        # Django ValidationError handler emits the same shape as Pydantic.
        first = body["detail"][0]
        assert first["loc"][0] == "body"
        assert "slug" in first["loc"]


@pytest.mark.django_db
class TestUpdateTag:
    def test_patches_fields(self, client):
        tag = TagFactory(name="Old", slug="old")
        client.get("/api/config")
        client.handler.enforce_csrf_checks = True
        token = client.cookies["csrftoken"].value

        response = client.patch(
            f"/api/example/tags/{tag.pk}",
            data={"name": "New"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "New"
        assert body["slug"] == "old"
        tag.refresh_from_db()
        assert tag.name == "New"

    def test_rejects_patch_without_csrf(self, client):
        tag = TagFactory()
        client.handler.enforce_csrf_checks = True
        response = client.patch(
            f"/api/example/tags/{tag.pk}",
            data={"name": "X"},
            content_type="application/json",
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestDeleteTag:
    def test_deletes_tag(self, client):
        tag = TagFactory()
        client.get("/api/config")
        client.handler.enforce_csrf_checks = True
        token = client.cookies["csrftoken"].value

        response = client.delete(
            f"/api/example/tags/{tag.pk}",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 204
        assert not Tag.objects.filter(pk=tag.pk).exists()

    def test_rejects_delete_without_csrf(self, client):
        tag = TagFactory()
        client.handler.enforce_csrf_checks = True
        response = client.delete(f"/api/example/tags/{tag.pk}")
        assert response.status_code == 403
        assert Tag.objects.filter(pk=tag.pk).exists()
