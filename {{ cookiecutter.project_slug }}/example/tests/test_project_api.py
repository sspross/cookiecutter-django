"""API tests for `example.api` Project endpoints."""

import pytest

from example.models import Project
from example.tests.factories import ProjectFactory, TagFactory


def _csrf(client):
    client.get("/api/config")
    client.handler.enforce_csrf_checks = True
    return client.cookies["csrftoken"].value


@pytest.mark.django_db
class TestListProjects:
    def test_returns_paginated_envelope_with_tags(self, client):
        backend = TagFactory(name="Backend", slug="backend")
        ProjectFactory(title="A", tags=[backend])
        ProjectFactory(title="B")

        response = client.get("/api/example/projects")

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        first = body["items"][0]
        assert {"id", "title", "status", "tags"} <= set(first.keys())
        # Tags are nested objects, not just ids.
        for item in body["items"]:
            for tag in item["tags"]:
                assert {"id", "name", "slug"} <= set(tag.keys())

    def test_filters_by_status(self, client):
        ProjectFactory(title="Draft", status="draft")
        ProjectFactory(title="Active", status="active")
        response = client.get("/api/example/projects?status=active")
        assert response.status_code == 200
        body = response.json()
        assert {item["title"] for item in body["items"]} == {"Active"}

    def test_filters_by_tag(self, client):
        backend = TagFactory(name="Backend", slug="backend")
        frontend = TagFactory(name="Frontend", slug="frontend")
        ProjectFactory(title="A", tags=[backend])
        ProjectFactory(title="B", tags=[frontend])
        response = client.get(f"/api/example/projects?tag={backend.pk}")
        assert response.status_code == 200
        body = response.json()
        assert {item["title"] for item in body["items"]} == {"A"}


@pytest.mark.django_db
class TestGetProject:
    def test_returns_single_project(self, client):
        backend = TagFactory(name="Backend", slug="backend")
        project = ProjectFactory(title="P", tags=[backend])

        response = client.get(f"/api/example/projects/{project.pk}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == project.pk
        assert body["title"] == "P"
        assert [t["slug"] for t in body["tags"]] == ["backend"]

    def test_returns_404_for_unknown(self, client):
        response = client.get("/api/example/projects/9999")
        assert response.status_code == 404


@pytest.mark.django_db
class TestCreateProject:
    def test_creates_with_csrf_and_assigns_tags(self, client):
        backend = TagFactory(name="Backend", slug="backend")
        token = _csrf(client)

        response = client.post(
            "/api/example/projects",
            data={
                "title": "Alpha",
                "description": "first",
                "status": "draft",
                "tag_ids": [backend.pk],
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["title"] == "Alpha"
        assert [t["slug"] for t in body["tags"]] == ["backend"]
        assert Project.objects.filter(title="Alpha").exists()

    def test_rejects_without_csrf(self, client):
        client.handler.enforce_csrf_checks = True
        response = client.post(
            "/api/example/projects",
            data={"title": "Alpha"},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_unknown_tag_id_returns_422(self, client):
        token = _csrf(client)
        response = client.post(
            "/api/example/projects",
            data={"title": "Alpha", "tag_ids": [9999]},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 422
        body = response.json()
        first = body["detail"][0]
        assert "tag_ids" in first["loc"]


@pytest.mark.django_db
class TestUpdateProject:
    def test_patch_changes_status(self, client):
        project = ProjectFactory(status="draft")
        token = _csrf(client)
        response = client.patch(
            f"/api/example/projects/{project.pk}",
            data={"status": "active"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 200
        project.refresh_from_db()
        assert project.status == "active"

    def test_patch_replaces_tags(self, client):
        backend = TagFactory(name="Backend", slug="backend")
        frontend = TagFactory(name="Frontend", slug="frontend")
        project = ProjectFactory(tags=[backend])
        token = _csrf(client)
        response = client.patch(
            f"/api/example/projects/{project.pk}",
            data={"tag_ids": [frontend.pk]},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 200
        assert [t.slug for t in project.tags.all()] == ["frontend"]


@pytest.mark.django_db
class TestDeleteProject:
    def test_deletes_with_csrf(self, client):
        project = ProjectFactory()
        token = _csrf(client)
        response = client.delete(
            f"/api/example/projects/{project.pk}",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 204
        assert not Project.objects.filter(pk=project.pk).exists()

    def test_rejects_delete_without_csrf(self, client):
        project = ProjectFactory()
        client.handler.enforce_csrf_checks = True
        response = client.delete(f"/api/example/projects/{project.pk}")
        assert response.status_code == 403
