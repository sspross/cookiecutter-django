"""End-to-end live test for the Task CRUD slice.

Walks: open a project → list tasks → filter → create → edit → delete.
Tasks are surfaced nested under the project's detail route.
"""

from datetime import date

from playwright.sync_api import expect

from core.tests.utils import StaticLiveServerWithArtifactsOnErrorTestCase
from example.tests.factories import ProjectFactory, TaskFactory


class TestTaskCrud(StaticLiveServerWithArtifactsOnErrorTestCase):
    def test_happy_path_through_task_crud(self):
        project = ProjectFactory(title="Walking skeleton", status="active")
        TaskFactory(
            project=project,
            title="Wire up Caddy",
            status="done",
            priority="high",
            due_date=date(2025, 1, 25),
        )
        TaskFactory(
            project=project,
            title="SPA bootstrap",
            status="in_progress",
            priority="high",
        )
        TaskFactory(
            project=project,
            title="Write README",
            status="todo",
            priority="low",
        )

        page = self.page
        page.goto(
            f"{self.live_server_url}/projects/{project.pk}"
        )

        list_region = page.get_by_test_id("tasks-list")
        expect(list_region).to_contain_text("Wire up Caddy", timeout=10_000)
        expect(list_region).to_contain_text("SPA bootstrap")
        expect(list_region).to_contain_text("Write README")

        # Filter to in_progress.
        page.get_by_test_id("tasks-filter-status").select_option("in_progress")
        expect(list_region).to_contain_text("SPA bootstrap")
        expect(list_region).not_to_contain_text("Wire up Caddy")
        expect(list_region).not_to_contain_text("Write README")
        page.get_by_test_id("tasks-filter-status").select_option("")

        # Create a new task.
        page.get_by_test_id("tasks-create-button").click()
        page.get_by_test_id("task-form-title").fill("Polish docs")
        page.get_by_test_id("task-form-priority").select_option("urgent")
        page.get_by_test_id("task-form-due-date").fill("2025-03-15")
        page.get_by_test_id("task-form-submit").click()
        expect(list_region).to_contain_text("Polish docs", timeout=5_000)

        # Edit the new task.
        new_row = list_region.locator("tr").filter(has_text="Polish docs")
        new_row.locator('[data-testid^="task-edit-"]').click()
        title_input = page.get_by_test_id("task-form-title")
        title_input.fill("")
        title_input.fill("Polish docs (final)")
        page.get_by_test_id("task-form-submit").click()
        expect(list_region).to_contain_text(
            "Polish docs (final)", timeout=5_000
        )

        # Delete it.
        edited_row = list_region.locator("tr").filter(
            has_text="Polish docs (final)"
        )
        edited_row.locator('[data-testid^="task-delete-"]').click()
        page.get_by_test_id("task-delete-confirm").click()
        expect(list_region).not_to_contain_text(
            "Polish docs (final)", timeout=5_000
        )
