"""End-to-end live test for the walking skeleton.

Boots the SPA via the deployed serving path (Django's `spa_shell` view
returns the collectstatic'd `index.html`), waits for the typed
openapi-fetch client to round-trip `/api/health`, and asserts the
response renders.
"""

from playwright.sync_api import expect

from core.tests.utils import StaticLiveServerWithArtifactsOnErrorTestCase


class TestSpaHealthRoundtrip(StaticLiveServerWithArtifactsOnErrorTestCase):
    def test_typed_health_call_renders(self):
        page = self.page
        page.goto(self.live_server_url)

        # The SPA bundle must load and TanStack Query has to fetch /api/health.
        status = page.get_by_test_id("health-status")
        expect(status).to_have_text("ok", timeout=10_000)
