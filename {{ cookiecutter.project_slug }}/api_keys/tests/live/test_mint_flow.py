"""End-to-end live test for the api_keys mint/revoke flow.

Demonstrates the full stack: Django session login -> SPA route ->
ninja API call -> modal with one-shot raw token -> revoke.
"""

from urllib.parse import urlparse

from api_keys import services as api_keys
from api_keys.tests.factories import UserFactory
from core.tests.utils import StaticLiveServerWithArtifactsOnErrorTestCase


class TestMintFlow(StaticLiveServerWithArtifactsOnErrorTestCase):
    def test_full_self_service_lifecycle(self):
        user = UserFactory(username="alice")
        user.set_password("pw-12345!")
        user.save()

        # Log in.
        login_url = f"{self.live_server_url}/accounts/login/"
        self.page.goto(login_url)
        self.page.fill('input[name="username"]', "alice")
        self.page.fill('input[name="password"]', "pw-12345!")
        self.page.click('button[type="submit"], input[type="submit"]')
        self.page.wait_for_load_state("networkidle")

        # Click the API sidebar nav item.
        self.page.click('[data-testid="sidebar"] >> text=API')
        self.page.wait_for_url("**/api-access")
        assert urlparse(self.page.url).path == "/api-access"

        # Empty state with CTA visible.
        self.page.wait_for_selector('[data-testid="api-keys-empty"]')

        # Mint via the empty-state CTA.
        self.page.click('[data-testid="empty-state-mint"]')
        self.page.fill('[data-testid="api-key-name"]', "laptop-cli")
        self.page.click('[data-testid="submit-mint"]')

        # Reveal modal: token visible + ack required.
        self.page.wait_for_selector('[data-testid="reveal-modal"]')
        token_text = self.page.locator('[data-testid="raw-token"]').inner_text()
        assert token_text.startswith(api_keys.TOKEN_PREFIX)
        # Esc must NOT close the reveal modal — the only exit is "ack".
        self.page.keyboard.press("Escape")
        assert self.page.locator('[data-testid="reveal-modal"]').is_visible()

        # Acknowledge to dismiss.
        self.page.click('[data-testid="ack-token"]')
        self.page.wait_for_selector('[data-testid="reveal-modal"]', state="detached")

        # The new key shows up in the list, marked Active.
        self.page.wait_for_selector('[data-testid="api-keys-table"]')
        row_text = self.page.locator('[data-testid="api-keys-table"]').inner_text()
        assert "laptop-cli" in row_text
        assert "Active" in row_text

        # Click revoke; confirm in the dialog.
        self.page.click('[data-testid^="revoke-"]')
        self.page.wait_for_selector('[data-testid="revoke-modal"]')
        self.page.click('[data-testid="confirm-revoke"]')
        self.page.wait_for_selector('[data-testid="revoke-modal"]', state="detached")

        # Row stays visible with a Revoked badge; revoke action is gone.
        self.page.wait_for_selector('[data-testid^="api-key-revoked-"]')
        row_text_after = self.page.locator(
            '[data-testid="api-keys-table"]'
        ).inner_text()
        assert "laptop-cli" in row_text_after
        assert "Revoked" in row_text_after
        assert self.page.locator('[data-testid^="revoke-"]').count() == 0
