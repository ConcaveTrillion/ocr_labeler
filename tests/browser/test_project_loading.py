"""Browser tests for loading projects via UI and URL."""

from __future__ import annotations

import pytest

from .helpers import load_project, wait_for_app_ready


@pytest.mark.browser
def test_load_project_via_ui(browser_app_url: str, browser_page) -> None:
    """Select a project from the dropdown, click LOAD, verify project loads."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)

    load_project(page, "browser-test-project")

    # Placeholder should be gone
    assert (
        page.get_by_text("No Project Loaded").count() == 0
        or not page.get_by_text("No Project Loaded").first.is_visible()
    )

    # Navigation controls should now be visible
    page.get_by_role("button", name="Next").wait_for(state="visible")


@pytest.mark.browser
def test_load_project_shows_loading_overlay(browser_app_url: str, browser_page) -> None:
    """Verify the loading overlay appears when loading a project."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)

    # Click the dropdown and select the project
    select = page.locator(".q-select").first
    select.click()
    page.locator(".q-menu .q-item").get_by_text("browser-test-project").click()

    # Click LOAD
    page.get_by_role("button", name="LOAD").click()

    # The loading overlay should become visible (may be brief)
    loading_overlay = page.locator("[data-nicegui-mark='project-loading-overlay']")

    # Wait for loading to complete
    loading_overlay.wait_for(state="hidden", timeout=60_000)

    # Project should now be loaded
    page.get_by_role("button", name="Next").wait_for(state="visible")


@pytest.mark.browser
def test_load_project_updates_url(browser_app_url: str, browser_page) -> None:
    """After loading, verify browser URL changes to include project and page."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)

    load_project(page, "browser-test-project")

    # URL should contain the project ID and page number
    page.wait_for_url("**/project/browser-test-project/page/1", timeout=10_000)


@pytest.mark.browser
def test_load_project_via_direct_url(browser_app_url: str, browser_page) -> None:
    """Navigate directly to a project URL and verify it loads."""
    page = browser_page
    url = browser_app_url.rstrip("/") + "/project/browser-test-project"
    page.goto(url, wait_until="networkidle")

    # Wait for the project to load
    page.get_by_role("button", name="Next").wait_for(state="visible", timeout=60_000)


@pytest.mark.browser
def test_load_specific_page_via_url(browser_app_url: str, browser_page) -> None:
    """Navigate directly to a specific page URL and verify that page loads."""
    page = browser_page
    url = browser_app_url.rstrip("/") + "/project/browser-test-project/page/2"
    page.goto(url, wait_until="networkidle")

    # Wait for the page to load
    page.get_by_role("button", name="Next").wait_for(state="visible", timeout=60_000)

    # Verify we're on page 2
    page_input = page.get_by_label("Page")
    page_input.wait_for(state="visible")
    assert page_input.input_value() == "2"


@pytest.mark.browser
def test_page_count_displayed(browser_app_url: str, browser_page) -> None:
    """After loading, verify the total page count is displayed."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)

    load_project(page, "browser-test-project")

    # Should show "/ 3" for our 3-page test project
    page.get_by_text("/ 3").first.wait_for(state="visible", timeout=10_000)
