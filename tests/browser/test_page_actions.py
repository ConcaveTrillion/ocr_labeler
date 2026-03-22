"""Browser tests for the page action buttons."""

from __future__ import annotations

import pytest

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded


@pytest.mark.browser
def test_action_buttons_present(browser_app_url: str, browser_page) -> None:
    """Verify Reload OCR, Save Page, Load Page buttons exist."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    page.get_by_role("button", name="Reload OCR").wait_for(state="visible")
    page.get_by_role("button", name="Save Page").wait_for(state="visible")
    page.get_by_role("button", name="Load Page").wait_for(state="visible")


@pytest.mark.browser
def test_page_name_shows_filename(browser_app_url: str, browser_page) -> None:
    """Verify the current image filename is displayed."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # The page name display should show the image filename (e.g., "001.png")
    page.get_by_text("001.png").first.wait_for(state="visible", timeout=10_000)


@pytest.mark.browser
def test_save_page_button_click(browser_app_url: str, browser_page) -> None:
    """Click Save Page and verify a success notification appears."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Click Save Page
    page.get_by_role("button", name="Save Page").click()

    # Wait for a notification to appear (NiceGUI uses Quasar notifications)
    # Notifications appear as q-notification elements
    page.locator(".q-notification").first.wait_for(state="visible", timeout=15_000)
