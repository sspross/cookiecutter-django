from playwright.sync_api import expect

from core.tests.utils import StaticLiveServerWithArtifactsOnErrorTestCase


class TestWidgetFunctionality(StaticLiveServerWithArtifactsOnErrorTestCase):
    def test_counter_button_increments_correctly(self):
        page = self.page

        page.goto(f"{self.live_server_url}/about/")

        # Wait for the button to be visible and verify initial state
        button = page.locator("button:has-text('count is')")
        button.wait_for(state="visible")

        # Verify initial counter state
        expect(button).to_contain_text("count is 0")

        # Click and verify count is 1
        button.click()
        expect(button).to_contain_text("count is 1")

        # Click and verify count is 2
        button.click()
        expect(button).to_contain_text("count is 2")

        # Click and verify count is 3
        button.click()
        expect(button).to_contain_text("count is 3")
