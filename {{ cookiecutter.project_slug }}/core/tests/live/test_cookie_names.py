from playwright.sync_api import Page, expect

from api_keys.tests.factories import UserFactory


def test_spa_writes_with_port_suffixed_cookie_names(
    page: Page, live_server, settings
) -> None:
    settings.SESSION_COOKIE_NAME = "sessionid_8001"
    settings.CSRF_COOKIE_NAME = "csrftoken_8001"
    UserFactory.create(username="alice")

    page.goto(f"{live_server.url}/accounts/login/")
    page.fill('input[name="username"]', "alice")
    page.fill('input[name="password"]', "pw-12345!")
    page.click('[data-testid="login-form"] button[type="submit"]')
    expect(page.locator('[data-testid="sidebar"]')).to_be_visible()

    page.goto(f"{live_server.url}/api-access")
    page.click('[data-testid="empty-state-mint"]')
    page.fill('[data-testid="api-key-name"]', "laptop-cli")
    page.click('[data-testid="submit-mint"]')
    expect(page.locator('[data-testid="reveal-modal"]')).to_be_visible()
    page.click('[data-testid="ack-token"]')
    page.wait_for_selector('[data-testid="reveal-modal"]', state="detached")

    sidebar = page.locator('[data-testid="sidebar"]')
    sidebar.get_by_role("button", name="Log out").click()
    page.wait_for_url("**/accounts/login/")
