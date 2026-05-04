"""Service tests for `example.services` (Task)."""

from datetime import date

import pytest
from django.core.exceptions import ValidationError

from example import services
from example.models import Project, Task
from example.tests.factories import ProjectFactory, TaskFactory


@pytest.mark.django_db
class TestCreateTask:
    def test_persists_task(self):
        project = ProjectFactory()
        task = services.create_task(
            project_id=project.pk,
            title="Write the docs",
            priority="high",
        )
        assert task.pk is not None
        assert task.project_id == project.pk
        assert task.priority == "high"

    def test_full_clean_rejects_invalid_status(self):
        project = ProjectFactory()
        with pytest.raises(ValidationError):
            services.create_task(
                project_id=project.pk, title="X", status="not-a-status"
            )

    def test_full_clean_rejects_blank_title(self):
        project = ProjectFactory()
        with pytest.raises(ValidationError):
            services.create_task(project_id=project.pk, title="")


@pytest.mark.django_db
class TestUpdateTask:
    def test_partial_update_changes_status(self):
        task = TaskFactory(status="todo")
        updated = services.update_task(task=task, status="in_progress")
        updated.refresh_from_db()
        assert updated.status == "in_progress"

    def test_can_clear_due_date_explicitly(self):
        task = TaskFactory(due_date=date(2025, 2, 1))
        updated = services.update_task(task=task, due_date=None)
        updated.refresh_from_db()
        assert updated.due_date is None

    def test_unspecified_fields_remain_unchanged(self):
        task = TaskFactory(due_date=date(2025, 2, 1), title="Keep due date")
        updated = services.update_task(task=task, title="New title")
        updated.refresh_from_db()
        assert updated.title == "New title"
        assert updated.due_date == date(2025, 2, 1)

    def test_unknown_field_raises_type_error(self):
        task = TaskFactory()
        with pytest.raises(TypeError):
            services.update_task(task=task, weird_field="x")


@pytest.mark.django_db
class TestDeleteTask:
    def test_removes_task(self):
        task = TaskFactory()
        services.delete_task(task=task)
        assert not Task.objects.filter(pk=task.pk).exists()


@pytest.mark.django_db
class TestProjectCascadeDelete:
    def test_deleting_project_deletes_its_tasks(self):
        project = ProjectFactory()
        project_pk = project.pk
        TaskFactory(project=project)
        TaskFactory(project=project)
        other = ProjectFactory()
        TaskFactory(project=other)

        services.delete_project(project=project)

        assert Project.objects.filter(pk=project_pk).count() == 0
        assert Task.objects.filter(project_id=project_pk).count() == 0
        # Tasks for the unrelated project are untouched.
        assert Task.objects.filter(project=other).count() == 1
