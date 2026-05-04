"""Filter tests for `example.filters.TaskFilters` in isolation."""

from datetime import date

import pytest

from example.filters import TaskFilters
from example.models import Task
from example.tests.factories import ProjectFactory, TaskFactory


@pytest.mark.django_db
class TestTaskFilters:
    def test_empty_filter_matches_everything(self):
        TaskFactory.create_batch(3)
        assert TaskFilters().filter(Task.objects.all()).count() == 3

    def test_status_priority_combined_is_and(self):
        p = ProjectFactory()
        TaskFactory(project=p, status="todo", priority="urgent", title="A")
        TaskFactory(project=p, status="done", priority="urgent", title="B")
        result = list(
            TaskFilters(status="todo", priority="urgent").filter(
                Task.objects.all()
            )
        )
        assert [t.title for t in result] == ["A"]

    def test_due_from_only(self):
        p = ProjectFactory()
        TaskFactory(project=p, due_date=date(2025, 1, 1), title="A")
        TaskFactory(project=p, due_date=date(2025, 2, 1), title="B")
        result = list(
            TaskFilters(due_from=date(2025, 1, 15)).filter(Task.objects.all())
        )
        assert [t.title for t in result] == ["B"]
