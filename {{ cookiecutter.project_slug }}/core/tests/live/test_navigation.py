from playwright.sync_api import expect

from core.tests.utils import StaticLiveServerWithArtifactsOnErrorTestCase


class TestBrowserNavigation(StaticLiveServerWithArtifactsOnErrorTestCase):
    """Test browser navigation functionality using Playwright."""

    def test_click_about_link_loads_about_page(self):
        """Test that clicking on the about link loads the about page."""
        page = self.page

        # Navigate to the home page
        page.goto(self.live_server_url)

        # Find and click the about link
        about_link = page.get_by_role("link", name="About")
        about_link.click()

        # Wait for navigation and verify we're on the about page
        page.wait_for_url(f"{self.live_server_url}/about/")

        # Wait for HTMX to settle if present
        page.wait_for_function(
            "!document.querySelector('.htmx-settling')", timeout=5000
        )

        # Verify the about page content is loaded
        expect(page).to_have_title("About")
        # Use the visible main element
        expect(page.locator("main").last).to_contain_text(
            "This is the about page"
        )
