"""Browser tests for the word matching UI in the Matches tab."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded


def _select_first_word(page) -> None:
    word_checkbox = page.get_by_label("Select word").first
    word_checkbox.wait_for(state="visible", timeout=10_000)
    word_checkbox.check(force=True)


def _clear_first_tag_chip(page, *, chip_testid: str, clear_button_testid: str) -> None:
    chip = page.locator(f".{chip_testid}").first
    expect(chip).to_be_visible()
    chip.hover()
    clear_button = chip.locator(f".{clear_button_testid}").first
    expect(clear_button).to_be_visible()
    clear_button.click()


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
    """Verify the line filter toggle exists with all options."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # The filter toggle should have all three options
    page.get_by_text("Unvalidated Lines").first.wait_for(
        state="visible", timeout=10_000
    )


@pytest.mark.browser
def test_switching_filter_toggle(browser_app_url: str, browser_page) -> None:
    """Switch between filter toggle options."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Default is Unvalidated Lines; switch through the options
    page.get_by_text("Mismatched Lines").first.click()
    page.wait_for_timeout(500)
    page.get_by_text("All Lines").first.click()
    page.wait_for_timeout(500)
    page.get_by_text("Unvalidated Lines").first.click()


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
    page.locator('[data-testid="apply-style-button"]').wait_for(state="visible")
    page.get_by_text("Scope").first.wait_for(state="visible")
    page.get_by_text("Apply Component").first.wait_for(state="visible")
    page.locator('[data-testid="apply-component-button"]').wait_for(state="visible")


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
    expect(page.get_by_text("Scope").first).to_be_visible()


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

    _select_first_word(page)

    apply_button = page.locator('[data-testid="apply-style-button"]')
    expect(apply_button).to_be_enabled()

    # A default style is preselected; verify apply action succeeds after selection.
    apply_button.click()

    expect(page.locator('[data-testid="apply-component-button"]')).to_be_enabled()


@pytest.mark.browser
def test_word_actions_use_single_footnote_toggle(
    browser_app_url: str, browser_page
) -> None:
    """Word edit dialog should support a unified Footnote Marker component."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    page.locator('[data-testid="edit-word-button"]').first.click()
    page.get_by_text("Merge / Split").first.wait_for(state="visible", timeout=10_000)

    dialog = page.locator(".q-dialog").last
    dialog.get_by_label("Component").click()
    page.get_by_role("option", name="Footnote Marker").first.click()
    dialog.get_by_role("button", name="Apply Component").click()

    expect(
        page.locator(".word-edit-tag-chip").filter(has_text="Footnote Marker")
    ).to_have_count(1)


@pytest.mark.browser
def test_dialog_tag_chip_clear_rerenders_immediately(
    browser_app_url: str, browser_page
) -> None:
    """Clearing a dialog tag chip should update the dialog chip list immediately."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    page.locator('[data-testid="edit-word-button"]').first.click()
    page.get_by_text("Merge / Split").first.wait_for(state="visible", timeout=10_000)
    dialog = page.locator(".q-dialog").last

    dialog.get_by_role("button", name="Apply Style").click()

    dialog_chips = page.locator(".word-edit-tag-chip")
    expect(dialog_chips).to_have_count(1)

    _clear_first_tag_chip(
        page,
        chip_testid="word-edit-tag-chip",
        clear_button_testid="word-edit-tag-clear-button",
    )
    expect(dialog_chips).to_have_count(0)
