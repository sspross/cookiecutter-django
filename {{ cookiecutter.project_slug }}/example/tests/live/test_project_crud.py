"""End-to-end live test for the Project CRUD slice.

Walks list → filter by status → filter by tag → create → detail → edit
→ delete. Mirrors the Tag live test, with the M2M tag picker in the
form and a real detail page (vs. the dialog-only Tag UX).
"""

from playwright.sync_api import expect

from core.tests.utils import StaticLiveServerWithArtifactsOnErrorTestCase
from example.tests.factories import ProjectFactory, TagFactory


class TestProjectCrud(StaticLiveServerWithArtifactsOnErrorTestCase):
    def test_happy_path_through_project_crud(self):
        backend = TagFactory(name="Backend", slug="backend")
        frontend = TagFactory(name="Frontend", slug="frontend")
        ProjectFactory(title="Walking skeleton", status="active", tags=[backend])
        ProjectFactory(title="Public docs", status="draft", tags=[frontend])
        ProjectFactory(title="Legacy migration", status="archived")

        page = self.page
        page.goto(f"{self.live_server_url}/projects")

        list_region = page.get_by_test_id("projects-list")
        expect(list_region).to_contain_text("Walking skeleton", timeout=10_000)
        expect(list_region).to_contain_text("Public docs")
        expect(list_region).to_contain_text("Legacy migration")

        # Filter by status (active).
        page.get_by_test_id("projects-filter-status").select_option("active")
        expect(list_region).to_contain_text("Walking skeleton")
        expect(list_region).not_to_contain_text("Public docs")
        page.get_by_test_id("projects-filter-status").select_option("")

        # Filter by tag.
        page.get_by_test_id("projects-filter-tag").select_option(str(backend.pk))
        expect(list_region).to_contain_text("Walking skeleton")
        expect(list_region).not_to_contain_text("Public docs")
        page.get_by_test_id("projects-filter-tag").select_option("")

        # Create a project with a tag attached.
        page.get_by_test_id("projects-create-button").click()
        page.get_by_test_id("project-form-title").fill("New initiative")
        page.get_by_test_id(f"project-form-tag-{frontend.pk}").locator(
            "input[type=checkbox]"
        ).check()
        page.get_by_test_id("project-form-status").select_option("active")
        page.get_by_test_id("project-form-submit").click()
        expect(list_region).to_contain_text("New initiative", timeout=5_000)

        # Visit the detail page for the new project.
        page.get_by_text("New initiative").click()
        detail_title = page.get_by_test_id("project-detail-title")
        expect(detail_title).to_have_text("New initiative", timeout=5_000)
        page.go_back()
        expect(list_region).to_contain_text("New initiative", timeout=5_000)

        # Edit the new project.
        new_row = list_region.locator("tr").filter(has_text="New initiative")
        new_row.locator('[data-testid^="project-edit-"]').click()
        title_input = page.get_by_test_id("project-form-title")
        title_input.fill("")
        title_input.fill("Refined initiative")
        page.get_by_test_id("project-form-submit").click()
        expect(list_region).to_contain_text("Refined initiative", timeout=5_000)

        # Delete it.
        refined_row = list_region.locator("tr").filter(
            has_text="Refined initiative"
        )
        refined_row.locator('[data-testid^="project-delete-"]').click()
        page.get_by_test_id("project-delete-confirm").click()
        expect(list_region).not_to_contain_text("Refined initiative", timeout=5_000)
