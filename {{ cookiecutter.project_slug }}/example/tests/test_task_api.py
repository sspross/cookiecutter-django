"""API tests for `example.api` Task endpoints."""

import pytest

from example.models import Task
from example.tests.factories import ProjectFactory, TaskFactory


def _csrf(client):
    client.get("/api/config")
    client.handler.enforce_csrf_checks = True
    return client.cookies["csrftoken"].value


@pytest.mark.django_db
class TestListTasks:
    def test_returns_paginated_envelope(self, client):
        TaskFactory.create_batch(2)
        response = client.get("/api/example/tasks")
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 2
        assert {"id", "project_id", "title", "status", "priority"} <= set(
            body["items"][0].keys()
        )

    def test_filters_by_project_via_query(self, client):
        p1 = ProjectFactory()
        p2 = ProjectFactory()
        TaskFactory(project=p1, title="A")
        TaskFactory(project=p2, title="B")
        response = client.get(f"/api/example/tasks?project={p1.pk}")
        assert response.status_code == 200
        body = response.json()
        assert {item["title"] for item in body["items"]} == {"A"}


@pytest.mark.django_db
class TestGetTask:
    def test_returns_task(self, client):
        task = TaskFactory(title="Solo")
        response = client.get(f"/api/example/tasks/{task.pk}")
        assert response.status_code == 200
        assert response.json()["title"] == "Solo"

    def test_returns_404_for_unknown(self, client):
        response = client.get("/api/example/tasks/9999")
        assert response.status_code == 404


@pytest.mark.django_db
class TestCreateTask:
    def test_creates_task_with_csrf(self, client):
        project = ProjectFactory()
        token = _csrf(client)
        response = client.post(
            "/api/example/tasks",
            data={
                "project_id": project.pk,
                "title": "New task",
                "priority": "high",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["project_id"] == project.pk
        assert body["title"] == "New task"
        assert Task.objects.filter(title="New task").exists()

    def test_rejects_create_without_csrf(self, client):
        project = ProjectFactory()
        client.handler.enforce_csrf_checks = True
        response = client.post(
            "/api/example/tasks",
            data={"project_id": project.pk, "title": "X"},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_invalid_status_returns_422(self, client):
        project = ProjectFactory()
        token = _csrf(client)
        response = client.post(
            "/api/example/tasks",
            data={
                "project_id": project.pk,
                "title": "X",
                "status": "nope",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        # Pydantic catches the invalid Literal value first.
        assert response.status_code == 422
        body = response.json()
        first = body["detail"][0]
        assert "loc" in first and "msg" in first


@pytest.mark.django_db
class TestUpdateTask:
    def test_patch_with_csrf(self, client):
        task = TaskFactory(status="todo")
        token = _csrf(client)
        response = client.patch(
            f"/api/example/tasks/{task.pk}",
            data={"status": "in_progress"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 200
        task.refresh_from_db()
        assert task.status == "in_progress"

    def test_can_clear_due_date(self, client):
        from datetime import date

        task = TaskFactory(due_date=date(2025, 2, 1))
        token = _csrf(client)
        response = client.patch(
            f"/api/example/tasks/{task.pk}",
            data={"due_date": None},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 200
        task.refresh_from_db()
        assert task.due_date is None


@pytest.mark.django_db
class TestDeleteTask:
    def test_delete_with_csrf(self, client):
        task = TaskFactory()
        token = _csrf(client)
        response = client.delete(
            f"/api/example/tasks/{task.pk}",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 204
        assert not Task.objects.filter(pk=task.pk).exists()

    def test_rejects_delete_without_csrf(self, client):
        task = TaskFactory()
        client.handler.enforce_csrf_checks = True
        response = client.delete(f"/api/example/tasks/{task.pk}")
        assert response.status_code == 403
