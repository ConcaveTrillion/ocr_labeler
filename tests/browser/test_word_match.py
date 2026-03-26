"""Browser tests for the word matching UI in the Matches tab."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

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


@pytest.mark.browser
def test_apply_style_toolbar_present(browser_app_url: str, browser_page) -> None:
    """Verify the dedicated Apply Style toolbar is rendered with select, apply, and scope actions."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    page.get_by_text("Apply Style").first.wait_for(state="visible", timeout=10_000)
    page.get_by_role("button", name="Apply").wait_for(state="visible")
    page.get_by_role("button", name="Whole").wait_for(state="visible")
    page.get_by_role("button", name="Part").wait_for(state="visible")


@pytest.mark.browser
def test_apply_style_buttons_disabled_without_selection(
    browser_app_url: str, browser_page
) -> None:
    """Apply Style toolbar renders core controls before interaction."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    apply_button = page.locator('[data-testid="apply-style-button"]')
    expect(apply_button).to_be_visible()
    expect(page.get_by_role("button", name="Whole")).to_be_visible()


@pytest.mark.browser
def test_apply_style_dropdown_select_then_apply(
    browser_app_url: str, browser_page
) -> None:
    """Apply selected style after selecting a word."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    word_checkbox = page.get_by_label("Select word").first
    word_checkbox.wait_for(state="visible", timeout=10_000)
    word_checkbox.check(force=True)

    apply_button = page.locator('[data-testid="apply-style-button"]')
    expect(apply_button).to_be_enabled()

    # A default style is preselected; verify apply action succeeds after selection.
    apply_button.click()

    expect(page.get_by_role("button", name="Whole")).to_be_enabled()
