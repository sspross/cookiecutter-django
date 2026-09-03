"""End-to-end live test for the api_keys mint/revoke flow.

Drives the full stack: Django session login -> SPA route -> ninja API call ->
one-shot raw token modal -> revoke. Web-first ``expect()`` auto-retries, which
absorbs animation timing. See CONTEXT.md for the live-test conventions.
"""

from django.conf import settings
from playwright.sync_api import Page, expect

from api_keys import services as api_keys
from api_keys.tests.factories import UserFactory


def test_full_self_service_lifecycle(page: Page, live_server):
    user = UserFactory(username="alice")
    user.set_password("pw-12345!")
    user.save()

    # Log in.
    page.goto(f"{live_server.url}/accounts/login/")
    page.fill('input[name="username"]', "alice")
    page.fill('input[name="password"]', "pw-12345!")
    page.click('button[type="submit"], input[type="submit"]')
    # Wait for the SPA shell rather than the discouraged "networkidle".
    sidebar = page.locator('[data-testid="sidebar"]')
    expect(sidebar).to_be_visible()

    # The ADR-0006 boot seam: lower layers can assert each source, but only a
    # browser proves the SPA reads both and renders them together.
    expect(sidebar).to_contain_text(settings.PROJECT_NAME)
    expect(sidebar).to_contain_text("Signed in as alice")

    # Click the API sidebar nav item.
    page.click('[data-testid="sidebar"] >> text=API')
    page.wait_for_url("**/api-access")

    # Empty state with CTA visible.
    expect(page.locator('[data-testid="api-keys-empty"]')).to_be_visible()

    # Mint via the empty-state CTA.
    page.click('[data-testid="empty-state-mint"]')
    page.fill('[data-testid="api-key-name"]', "laptop-cli")
    page.click('[data-testid="submit-mint"]')

    # Reveal modal: token visible + ack required.
    expect(page.locator('[data-testid="reveal-modal"]')).to_be_visible()
    expect(page.locator('[data-testid="raw-token"]')).to_contain_text(
        api_keys.TOKEN_PREFIX
    )
    # Esc must NOT close the reveal modal — the only exit is "ack".
    page.keyboard.press("Escape")
    expect(page.locator('[data-testid="reveal-modal"]')).to_be_visible()

    # Acknowledge to dismiss.
    page.click('[data-testid="ack-token"]')
    page.wait_for_selector('[data-testid="reveal-modal"]', state="detached")

    # The new key shows up in the list, marked Active.
    expect(page.locator('[data-testid="api-keys-table"]')).to_contain_text("laptop-cli")
    expect(page.locator('[data-testid="api-keys-table"]')).to_contain_text("Active")

    # Click revoke; confirm in the dialog.
    page.click('[data-testid^="revoke-"]')
    expect(page.locator('[data-testid="revoke-modal"]')).to_be_visible()
    page.click('[data-testid="confirm-revoke"]')
    page.wait_for_selector('[data-testid="revoke-modal"]', state="detached")

    # Row stays visible with a Revoked badge; revoke action is gone.
    expect(page.locator('[data-testid^="api-key-revoked-"]')).to_be_visible()
    expect(page.locator('[data-testid="api-keys-table"]')).to_contain_text("laptop-cli")
    expect(page.locator('[data-testid="api-keys-table"]')).to_contain_text("Revoked")
    expect(page.locator('[data-testid^="revoke-"]')).to_have_count(0)
