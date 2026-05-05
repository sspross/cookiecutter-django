"""End-to-end live test for the Tag CRUD slice.

Boots the SPA via the deployed serving path and walks the happy path:
list → filter → create → detail → edit → delete.
"""

from playwright.sync_api import expect

from core.tests.utils import StaticLiveServerWithArtifactsOnErrorTestCase
from example.tests.factories import TagFactory


class TestTagCrud(StaticLiveServerWithArtifactsOnErrorTestCase):
    def test_happy_path_through_tag_crud(self):
        TagFactory(name="Backend", slug="backend")
        TagFactory(name="Frontend", slug="frontend")

        page = self.page
        page.goto(f"{self.live_server_url}/tags")

        # The list renders the seeded tags.
        list_region = page.get_by_test_id("tags-list")
        expect(list_region).to_contain_text("Backend", timeout=10_000)
        expect(list_region).to_contain_text("Frontend")

        # Filter narrows the list.
        page.get_by_test_id("tags-filter-name").fill("back")
        expect(list_region).to_contain_text("Backend")
        expect(list_region).not_to_contain_text("Frontend")
        page.get_by_test_id("tags-filter-name").fill("")

        # Create a new tag via the dialog.
        page.get_by_test_id("tags-create-button").click()
        page.get_by_test_id("tag-form-name").fill("Mobile")
        page.get_by_test_id("tag-form-slug").fill("mobile")
        page.get_by_test_id("tag-form-submit").click()
        expect(list_region).to_contain_text("Mobile", timeout=5_000)

        # Edit the new tag.
        page.get_by_test_id("tag-edit-mobile").click()
        name_input = page.get_by_test_id("tag-form-name")
        name_input.fill("")
        name_input.fill("Mobile Apps")
        page.get_by_test_id("tag-form-submit").click()
        expect(list_region).to_contain_text("Mobile Apps", timeout=5_000)

        # Delete the tag.
        page.get_by_test_id("tag-delete-mobile").click()
        page.get_by_test_id("tag-delete-confirm").click()
        expect(list_region).not_to_contain_text("Mobile Apps", timeout=5_000)
