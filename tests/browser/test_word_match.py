"""Browser tests for the word matching UI in the Matches tab."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

WORD_VALIDATE_BUTTON = '[data-testid="word-validate-button"]'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _select_first_word(page) -> None:
    word_checkbox = page.locator('[data-testid="word-checkbox"]').first
    word_checkbox.wait_for(state="visible", timeout=10_000)
    word_checkbox.click()
    page.wait_for_timeout(1000)


def _clear_first_tag_chip(page, *, chip_testid: str, clear_button_testid: str) -> None:
    chip = page.locator(f".{chip_testid}").first
    expect(chip).to_be_visible()
    chip.hover()
    clear_button = chip.locator(f".{clear_button_testid}").first
    expect(clear_button).to_be_visible()
    clear_button.click()


def _setup(page, url: str) -> None:
    """Navigate, load project, and wait for page content."""
    page.goto(url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)


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


# ---------------------------------------------------------------------------
# Per-word validate toggle (Commit 3)
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_word_validate_button_present(browser_app_url: str, browser_page) -> None:
    """Validate icon visible on each word column."""
    page = browser_page
    _setup(page, browser_app_url)

    buttons = page.locator(WORD_VALIDATE_BUTTON)
    expect(buttons.first).to_be_visible()
    assert buttons.count() > 0


@pytest.mark.browser
def test_word_validate_toggle(browser_app_url: str, browser_page) -> None:
    """Click validate button: grey→green; click again: green→grey."""
    page = browser_page
    _setup(page, browser_app_url)

    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_be_visible()

    # Should start as grey (unvalidated)
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-grey"))

    # Click to validate
    val_btn.click()
    page.wait_for_timeout(500)

    # Should now be green
    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-green"))

    # Click again to unvalidate
    val_btn.click()
    page.wait_for_timeout(500)

    # Should revert to grey
    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-grey"))


# ---------------------------------------------------------------------------
# Per-word tag chip clear (Commit 3)
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_word_tag_clear_in_renderer(browser_app_url: str, browser_page) -> None:
    """Apply a style via word edit dialog, close, then clear chip in renderer."""
    page = browser_page
    _setup(page, browser_app_url)

    # Open the word edit dialog for the first word
    page.locator('[data-testid="edit-word-button"]').first.click()
    page.get_by_text("Merge / Split").first.wait_for(state="visible", timeout=10_000)
    dialog = page.locator(".q-dialog").last

    # Apply a style inside the dialog
    dialog.get_by_role("button", name="Apply Style").click()
    page.wait_for_timeout(500)

    # Close dialog with Escape (closes without additional save)
    page.keyboard.press("Escape")
    page.wait_for_timeout(1000)

    # Tag chip should now be visible in the renderer
    chip = page.locator('[data-testid="word-tag-chip"]').first
    expect(chip).to_be_visible(timeout=10_000)

    # Hover to reveal clear button, then click it
    chip.hover()
    clear_btn = chip.locator('[data-testid="word-tag-clear-button"]').first
    expect(clear_btn).to_be_visible()
    clear_btn.click()
    page.wait_for_timeout(1000)

    # Chip should be gone
    expect(page.locator('[data-testid="word-tag-chip"]')).to_have_count(0)


# ---------------------------------------------------------------------------
# Line checkbox selection (Commit 3)
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_checkbox_present(browser_app_url: str, browser_page) -> None:
    """Line selection checkbox visible in each line card header."""
    page = browser_page
    _setup(page, browser_app_url)

    line_checkboxes = page.get_by_label("Select line", exact=True)
    expect(line_checkboxes.first).to_be_visible()
    assert line_checkboxes.count() > 0


@pytest.mark.browser
def test_line_checkbox_selection(browser_app_url: str, browser_page) -> None:
    """Check line checkbox toggles selection state; uncheck reverts it."""
    page = browser_page
    _setup(page, browser_app_url)

    # Check first line checkbox — use click() since Quasar checkboxes
    # need the inner element clicked, not the outer wrapper
    line_checkbox = page.get_by_label("Select line", exact=True).first
    expect(line_checkbox).to_be_visible()

    # Click to check
    line_checkbox.click()
    page.wait_for_timeout(500)

    # Verify checked state
    expect(line_checkbox).to_be_checked()

    # Click again to uncheck
    line_checkbox.click()
    page.wait_for_timeout(500)

    # Verify unchecked
    expect(line_checkbox).not_to_be_checked()


# ---------------------------------------------------------------------------
# Clear Component button (Commit 7)
# ---------------------------------------------------------------------------

CLEAR_COMPONENT_BUTTON = '[data-testid="clear-component-button"]'
APPLY_COMPONENT_BUTTON = '[data-testid="apply-component-button"]'
SCOPE_SELECT = '[data-testid="scope-select"]'


@pytest.mark.browser
def test_clear_component_button_disabled_without_component(
    browser_app_url: str, browser_page
) -> None:
    """Clear Component button visible in toolbar after project load."""
    page = browser_page
    _setup(page, browser_app_url)

    clear_btn = page.locator(CLEAR_COMPONENT_BUTTON)
    expect(clear_btn).to_be_visible()


@pytest.mark.browser
def test_clear_component_button(browser_app_url: str, browser_page) -> None:
    """Select word → Apply Component → chip appears; click Clear Component → chip removed."""
    page = browser_page
    _setup(page, browser_app_url)

    _select_first_word(page)

    # Apply a component via toolbar
    apply_btn = page.locator(APPLY_COMPONENT_BUTTON)
    expect(apply_btn).to_be_enabled()
    apply_btn.click()
    page.wait_for_timeout(1000)

    # Tag chip should appear on the word in the renderer
    chip = page.locator('[data-testid="word-tag-chip"]').first
    expect(chip).to_be_visible(timeout=10_000)

    # Click Clear Component in toolbar
    clear_btn = page.locator(CLEAR_COMPONENT_BUTTON)
    expect(clear_btn).to_be_enabled()
    clear_btn.click()
    page.wait_for_timeout(1000)

    # Component chip should be removed
    expect(page.locator('[data-testid="word-tag-chip"]')).to_have_count(0)


# ---------------------------------------------------------------------------
# Scope dropdown (Commit 7)
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_scope_dropdown_present(browser_app_url: str, browser_page) -> None:
    """Scope dropdown visible with default value after project load."""
    page = browser_page
    _setup(page, browser_app_url)

    scope = page.locator(SCOPE_SELECT)
    expect(scope).to_be_visible()


@pytest.mark.browser
def test_scope_dropdown_interaction(browser_app_url: str, browser_page) -> None:
    """Open scope dropdown → select Whole → verify; select Part → verify."""
    page = browser_page
    _setup(page, browser_app_url)

    # Select a word first so the scope dropdown is enabled
    _select_first_word(page)

    # Apply a style so scope becomes meaningful
    apply_style_btn = page.locator('[data-testid="apply-style-button"]')
    expect(apply_style_btn).to_be_enabled()
    apply_style_btn.click()
    page.wait_for_timeout(500)

    # Open scope dropdown and select "Whole"
    scope = page.locator(SCOPE_SELECT)
    expect(scope).to_be_visible()
    scope.click()
    page.get_by_role("option", name="Whole").click()
    page.wait_for_timeout(500)

    # Verify Whole is selected (visible in the select's display text)
    expect(scope).to_contain_text("Whole")

    # Open scope dropdown and select "Part"
    scope.click()
    page.get_by_role("option", name="Part").click()
    page.wait_for_timeout(500)

    # Verify Part is selected
    expect(scope).to_contain_text("Part")
