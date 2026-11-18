import re

from playwright.sync_api import Locator, Page, ViewportSize, expect

from api_keys import services as api_keys
from users.tests.factories import UserFactory

DESKTOP: ViewportSize = {"width": 1280, "height": 720}
MOBILE: ViewportSize = {"width": 390, "height": 800}
DARK_CLASS = re.compile(r"\bdark\b")


def test_full_self_service_lifecycle(page: Page, live_server, settings) -> None:
    _suffix_the_cookie_names_like_a_local_stack(settings)
    UserFactory.create(username="alice")

    sidebar = _log_in(page, live_server.url)
    _see_the_server_rendered_constant_next_to_the_api_fetched_user(sidebar, settings)
    _open_api_access_and_see_the_empty_state(page)
    _mint_a_key_from_the_empty_state(page)
    _see_the_token_in_a_modal_that_escape_does_not_close(page)
    _copy_the_token_and_see_the_button_confirm_then_reset(page)
    _acknowledge_the_token(page)
    _see_the_new_key_listed_as_active(page)
    _revoke_the_key_and_confirm(page)
    _see_the_key_still_listed_as_revoked_without_a_revoke_action(page)
    _see_the_color_mode_follow_the_system_setting(page)
    _pick_a_color_mode_in_one_toggle_and_see_the_other_toggle_show_it(page, sidebar)
    _see_the_mobile_nav_close_after_navigating(page, live_server.url)
    _log_out(page, sidebar)


def _suffix_the_cookie_names_like_a_local_stack(settings) -> None:
    settings.SESSION_COOKIE_NAME = "sessionid_stack"
    settings.CSRF_COOKIE_NAME = "csrftoken_stack"


def _log_in(page: Page, base_url: str) -> Locator:
    page.goto(f"{base_url}/accounts/login/")
    page.fill('input[name="username"]', "alice")
    page.fill('input[name="password"]', "pw-12345!")
    page.click('[data-testid="login-form"] button[type="submit"]')
    sidebar = page.locator('[data-testid="sidebar"]')
    expect(sidebar).to_be_visible()
    return sidebar


def _see_the_server_rendered_constant_next_to_the_api_fetched_user(
    sidebar: Locator, settings
) -> None:
    expect(sidebar).to_contain_text(settings.PROJECT_NAME)
    expect(sidebar).to_contain_text("Signed in as alice")


def _open_api_access_and_see_the_empty_state(page: Page) -> None:
    page.click('[data-testid="sidebar"] >> text=API')
    page.wait_for_url("**/api-access")
    expect(page.locator('[data-testid="api-keys-empty"]')).to_be_visible()


def _mint_a_key_from_the_empty_state(page: Page) -> None:
    page.click('[data-testid="empty-state-mint"]')
    page.fill('[data-testid="api-key-name"]', "laptop-cli")
    page.click('[data-testid="submit-mint"]')


def _see_the_token_in_a_modal_that_escape_does_not_close(page: Page) -> None:
    expect(page.locator('[data-testid="reveal-modal"]')).to_be_visible()
    expect(page.locator('[data-testid="raw-token"]')).to_contain_text(
        api_keys.TOKEN_PREFIX
    )
    page.keyboard.press("Escape")
    expect(page.locator('[data-testid="reveal-modal"]')).to_be_visible()


def _copy_the_token_and_see_the_button_confirm_then_reset(page: Page) -> None:
    page.context.grant_permissions(["clipboard-write"])
    copy_token = page.locator('[data-testid="copy-token"]')
    copy_token.click()
    expect(copy_token).to_have_text("Copied!")
    expect(copy_token).to_have_text("Copy to clipboard")


def _acknowledge_the_token(page: Page) -> None:
    page.click('[data-testid="ack-token"]')
    page.wait_for_selector('[data-testid="reveal-modal"]', state="detached")


def _see_the_new_key_listed_as_active(page: Page) -> None:
    expect(page.locator('[data-testid="api-keys-table"]')).to_contain_text("laptop-cli")
    expect(page.locator('[data-testid="api-keys-table"]')).to_contain_text("Active")


def _revoke_the_key_and_confirm(page: Page) -> None:
    page.click('[data-testid^="revoke-"]')
    expect(page.locator('[data-testid="revoke-modal"]')).to_be_visible()
    page.click('[data-testid="confirm-revoke"]')
    page.wait_for_selector('[data-testid="revoke-modal"]', state="detached")


def _see_the_key_still_listed_as_revoked_without_a_revoke_action(page: Page) -> None:
    expect(page.locator('[data-testid^="api-key-revoked-"]')).to_be_visible()
    expect(page.locator('[data-testid="api-keys-table"]')).to_contain_text("laptop-cli")
    expect(page.locator('[data-testid="api-keys-table"]')).to_contain_text("Revoked")
    expect(page.locator('[data-testid^="revoke-"]')).to_have_count(0)


def _see_the_color_mode_follow_the_system_setting(page: Page) -> None:
    page.emulate_media(color_scheme="dark")
    expect(page.locator("html")).to_have_class(DARK_CLASS)
    page.emulate_media(color_scheme="light")
    expect(page.locator("html")).not_to_have_class(DARK_CLASS)


def _pick_a_color_mode_in_one_toggle_and_see_the_other_toggle_show_it(
    page: Page, sidebar: Locator
) -> None:
    mobile_nav = page.locator("#mobile-nav")

    page.set_viewport_size(MOBILE)
    page.get_by_role("button", name="Open menu").click()
    mobile_nav.locator("label", has_text="Dark").click()
    expect(page.locator("html")).to_have_class(DARK_CLASS)
    page.set_viewport_size(DESKTOP)
    expect(sidebar.get_by_role("radio", name="Dark")).to_be_checked()

    sidebar.locator("label", has_text="System").click()
    expect(page.locator("html")).not_to_have_class(DARK_CLASS)
    page.set_viewport_size(MOBILE)
    expect(mobile_nav.get_by_role("radio", name="System")).to_be_checked()
    page.get_by_role("button", name="Close menu").click()
    page.set_viewport_size(DESKTOP)


def _see_the_mobile_nav_close_after_navigating(page: Page, base_url: str) -> None:
    page.set_viewport_size(MOBILE)
    page.get_by_role("button", name="Open menu").click()
    mobile_nav = page.locator("#mobile-nav")
    mobile_nav.get_by_role("link", name="Dashboard").click()
    page.wait_for_url(f"{base_url}/")
    expect(mobile_nav).to_have_count(0)
    page.set_viewport_size(DESKTOP)


def _log_out(page: Page, sidebar: Locator) -> None:
    sidebar.get_by_role("button", name="Log out").click()
    page.wait_for_url("**/accounts/login/")
