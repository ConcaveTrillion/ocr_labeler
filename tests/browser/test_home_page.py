"""Browser tests for the home page before any project is loaded."""

from __future__ import annotations

import pytest

from .helpers import wait_for_app_ready


@pytest.mark.browser
def test_placeholder_text_and_icon(browser_app_url: str, browser_page) -> None:
    """Verify placeholder text and icon appear on the home page."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")

    page.get_by_text("No Project Loaded").first.wait_for(state="visible")
    page.get_by_text("Select a project above and click LOAD to begin.").first.wait_for(
        state="visible"
    )


@pytest.mark.browser
def test_project_dropdown_present(browser_app_url: str, browser_page) -> None:
    """Verify the Project dropdown is present on the home page."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)

    page.get_by_text("Project").first.wait_for(state="visible")
    # The Quasar select element should be present
    select = page.locator(".q-select").first
    select.wait_for(state="visible")


@pytest.mark.browser
def test_load_button_present(browser_app_url: str, browser_page) -> None:
    """Verify the LOAD button is visible on the home page."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)

    page.get_by_role("button", name="LOAD").wait_for(state="visible")


@pytest.mark.browser
def test_dropdown_lists_test_project(browser_app_url: str, browser_page) -> None:
    """Verify the test project appears in the dropdown options."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)

    # Click the dropdown to open it
    select = page.locator(".q-select").first
    select.click()

    # Verify our test project is listed in the dropdown popup
    page.locator(".q-menu .q-item").get_by_text("browser-test-project").wait_for(
        state="visible", timeout=5000
    )


@pytest.mark.browser
def test_no_navigation_before_load(browser_app_url: str, browser_page) -> None:
    """Verify navigation controls are NOT visible before loading a project."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)

    # Navigation buttons should not be visible
    assert page.get_by_role("button", name="Prev").count() == 0
    assert page.get_by_role("button", name="Next").count() == 0
    assert page.get_by_role("button", name="Go To:").count() == 0
