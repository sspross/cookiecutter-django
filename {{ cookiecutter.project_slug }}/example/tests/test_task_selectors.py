"""Selector tests for `example.selectors.list_tasks` / `get_task`."""

from datetime import date

import pytest

from example import selectors
from example.filters import TaskFilters
from example.tests.factories import ProjectFactory, TaskFactory


@pytest.mark.django_db
class TestListTasks:
    def test_filters_by_project(self):
        p1 = ProjectFactory(title="P1")
        p2 = ProjectFactory(title="P2")
        TaskFactory(project=p1, title="A")
        TaskFactory(project=p1, title="B")
        TaskFactory(project=p2, title="C")

        result = list(
            selectors.list_tasks(filters=TaskFilters(project=p1.pk))
        )
        assert {t.title for t in result} == {"A", "B"}

    def test_filters_combine_status_and_priority(self):
        p = ProjectFactory()
        TaskFactory(project=p, status="todo", priority="high", title="X")
        TaskFactory(project=p, status="todo", priority="low", title="Y")
        TaskFactory(project=p, status="done", priority="high", title="Z")

        result = list(
            selectors.list_tasks(
                filters=TaskFilters(status="todo", priority="high")
            )
        )
        assert {t.title for t in result} == {"X"}

    def test_due_date_range_inclusive(self):
        p = ProjectFactory()
        TaskFactory(project=p, due_date=date(2025, 1, 10), title="Early")
        TaskFactory(project=p, due_date=date(2025, 1, 20), title="Mid")
        TaskFactory(project=p, due_date=date(2025, 2, 10), title="Late")

        result = list(
            selectors.list_tasks(
                filters=TaskFilters(
                    due_from=date(2025, 1, 15), due_to=date(2025, 2, 15)
                )
            )
        )
        assert {t.title for t in result} == {"Mid", "Late"}

    def test_default_ordering_by_due_date_then_priority_then_created(self):
        p = ProjectFactory()
        TaskFactory(
            project=p, title="Later",  due_date=date(2025, 2, 10), priority="urgent"
        )
        TaskFactory(
            project=p, title="Earlier", due_date=date(2025, 1, 10), priority="low"
        )
        TaskFactory(project=p, title="NoDue", due_date=None, priority="high")

        result = list(selectors.list_tasks())
        # Postgres puts NULLs last for ASC ordering by default in Django,
        # but SQLite (test backend) puts them first. Either way `Earlier`
        # comes before `Later`.
        titles = [t.title for t in result]
        assert titles.index("Earlier") < titles.index("Later")


@pytest.mark.django_db
class TestGetTask:
    def test_returns_task_by_pk(self):
        task = TaskFactory()
        assert selectors.get_task(task_id=task.pk) == task
