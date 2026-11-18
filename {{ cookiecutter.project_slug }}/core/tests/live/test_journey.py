import re

from playwright.sync_api import Page, expect

from api_keys import services as api_keys
from users.tests.factories import UserFactory


def test_full_self_service_lifecycle(page: Page, live_server, settings) -> None:
    # A local stack suffixes both names; only a browser proves the SPA still writes.
    settings.SESSION_COOKIE_NAME = "sessionid_stack"
    settings.CSRF_COOKIE_NAME = "csrftoken_stack"
    UserFactory.create(username="alice")

    # Log in.
    page.goto(f"{live_server.url}/accounts/login/")
    page.fill('input[name="username"]', "alice")
    page.fill('input[name="password"]', "pw-12345!")
    page.click('[data-testid="login-form"] button[type="submit"]')
    sidebar = page.locator('[data-testid="sidebar"]')
    expect(sidebar).to_be_visible()

    # ADR-0006 boot seam: only a browser proves the SPA renders both sources together.
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
    page.keyboard.press("Escape")
    expect(page.locator('[data-testid="reveal-modal"]')).to_be_visible()

    # The copy button confirms, then goes back to its label.
    page.context.grant_permissions(["clipboard-write"])
    copy_token = page.locator('[data-testid="copy-token"]')
    copy_token.click()
    expect(copy_token).to_have_text("Copied!")
    expect(copy_token).to_have_text("Copy to clipboard")

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

    # On "system" the color mode follows the system setting.
    dark = re.compile(r"\bdark\b")
    page.emulate_media(color_scheme="dark")
    expect(page.locator("html")).to_have_class(dark)
    page.emulate_media(color_scheme="light")
    expect(page.locator("html")).not_to_have_class(dark)

    # The mobile nav closes after navigating.
    page.set_viewport_size({"width": 390, "height": 800})
    page.get_by_role("button", name="Open menu").click()
    mobile_nav = page.locator("#mobile-nav")
    mobile_nav.get_by_role("link", name="Dashboard").click()
    page.wait_for_url(f"{live_server.url}/")
    expect(mobile_nav).to_have_count(0)
    page.set_viewport_size({"width": 1280, "height": 720})

    # Log out.
    sidebar.get_by_role("button", name="Log out").click()
    page.wait_for_url("**/accounts/login/")
