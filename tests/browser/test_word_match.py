"""Browser tests for the word matching UI in the Matches tab."""

from __future__ import annotations

import pytest

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded


@pytest.mark.browser
def test_word_match_toolbar_present(browser_app_url: str, browser_page) -> None:
    """Verify the word match toolbar with scope rows is rendered."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # The Matches tab is default, toolbar scope labels should be visible
    page.get_by_text("Page").first.wait_for(state="visible", timeout=10_000)
    page.get_by_text("Paragraph").first.wait_for(state="visible")
    page.get_by_text("Line").first.wait_for(state="visible")
    page.get_by_text("Word").first.wait_for(state="visible")


@pytest.mark.browser
def test_filter_toggle_present(browser_app_url: str, browser_page) -> None:
    """Verify the Mismatched Lines / All Lines filter toggle exists."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # The filter toggle should have "Mismatched Lines" and "All Lines" options
    page.get_by_text("Mismatched Lines").first.wait_for(state="visible", timeout=10_000)


@pytest.mark.browser
def test_switching_filter_toggle(browser_app_url: str, browser_page) -> None:
    """Switch between Mismatched Lines and All Lines filter."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Click "All Lines" toggle
    page.get_by_text("All Lines").first.click()

    # Wait for content to update, then switch back
    page.wait_for_timeout(500)
    page.get_by_text("Mismatched Lines").first.click()


@pytest.mark.browser
def test_stats_label_visible(browser_app_url: str, browser_page) -> None:
    """Verify the stats label with match info is visible."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # The analytics icon should be present in the stats row
    page.locator("text=analytics").first.wait_for(state="visible", timeout=10_000)
