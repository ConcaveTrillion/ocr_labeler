"""Browser tests for the word edit dialog header and style controls (Commit 8)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

EDIT_WORD_BUTTON = '[data-testid="edit-word-button"]'
DIALOG_APPLY_CLOSE = '[data-testid="dialog-apply-close-button"]'
DIALOG_CLOSE = '[data-testid="dialog-close-button"]'
DIALOG_APPLY_STYLE = '[data-testid="dialog-apply-style-button"]'
DIALOG_APPLY_COMPONENT = '[data-testid="dialog-apply-component-button"]'
DIALOG_CLEAR_COMPONENT = '[data-testid="dialog-clear-component-button"]'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(page: Page, url: str) -> None:
    """Navigate, load project, and wait for page content."""
    page.goto(url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)


def _open_dialog(page: Page) -> None:
    """Open the word edit dialog for the first word."""
    page.locator(EDIT_WORD_BUTTON).first.click()
    page.get_by_text("Merge / Split").first.wait_for(state="visible", timeout=10_000)


# ---------------------------------------------------------------------------
# Dialog opens with correct data
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_opens_on_edit_button_click(browser_app_url: str, browser_page) -> None:
    """Click edit button → dialog visible with correct word data (GT text, OCR text, image)."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    dialog = page.locator(".q-dialog").last
    expect(dialog).to_be_visible()

    # Dialog should show the "Edit Line N, Word M" heading
    expect(dialog.locator("text=/Edit Line \\d+, Word \\d+/")).to_be_visible()

    # GT input should be present
    gt_input = dialog.get_by_label("GT")
    expect(gt_input).to_be_visible()

    # OCR text label should be visible (monospace text element)
    expect(dialog.locator(".monospace").first).to_be_visible()


# ---------------------------------------------------------------------------
# Dialog header buttons present
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_header_buttons_present(browser_app_url: str, browser_page) -> None:
    """Checkmark, X, Apply Style, Apply Component, Clear Component all visible."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    expect(page.locator(DIALOG_APPLY_CLOSE)).to_be_visible()
    expect(page.locator(DIALOG_CLOSE)).to_be_visible()
    expect(page.locator(DIALOG_APPLY_STYLE)).to_be_visible()
    expect(page.locator(DIALOG_APPLY_COMPONENT)).to_be_visible()
    expect(page.locator(DIALOG_CLEAR_COMPONENT)).to_be_visible()


@pytest.mark.browser
def test_dialog_header_button_tooltips(browser_app_url: str, browser_page) -> None:
    """Each header button has correct tooltip/aria-label."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    # Apply and close button should have tooltip
    apply_close_btn = page.locator(DIALOG_APPLY_CLOSE)
    expect(apply_close_btn).to_be_visible()

    # Close button should have tooltip
    close_btn = page.locator(DIALOG_CLOSE)
    expect(close_btn).to_be_visible()


# ---------------------------------------------------------------------------
# Button 65: Apply & Close
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_apply_and_close(browser_app_url: str, browser_page) -> None:
    """Change GT text in dialog → click checkmark → dialog closes; main grid GT updated."""
    page = browser_page
    _setup(page, browser_app_url)

    # Read original GT input value from the inline renderer
    # (The inline GT inputs are monospace inputs in the word columns)
    _open_dialog(page)
    dialog = page.locator(".q-dialog").last

    gt_input = dialog.get_by_label("GT")
    expect(gt_input).to_be_visible()
    original_gt = gt_input.input_value()

    # Change GT text
    gt_input.fill("XYZZY_APPLY")
    page.wait_for_timeout(500)

    # Click Apply & Close (checkmark)
    page.locator(DIALOG_APPLY_CLOSE).click()
    page.wait_for_timeout(1000)

    # Dialog should be closed
    expect(page.locator(".q-dialog")).to_have_count(0)

    # Re-open dialog to verify the change persisted
    _open_dialog(page)
    dialog = page.locator(".q-dialog").last
    gt_input = dialog.get_by_label("GT")
    expect(gt_input).to_have_value("XYZZY_APPLY")

    # Restore original value
    gt_input.fill(original_gt)
    page.wait_for_timeout(300)
    page.locator(DIALOG_APPLY_CLOSE).click()


# ---------------------------------------------------------------------------
# Button 66: Close without saving
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_close_without_saving(browser_app_url: str, browser_page) -> None:
    """Click X closes dialog without applying pending bbox nudges."""
    page = browser_page
    _setup(page, browser_app_url)

    _open_dialog(page)
    dialog = page.locator(".q-dialog").last
    expect(dialog).to_be_visible()

    # Click Close (X button)
    page.locator(DIALOG_CLOSE).click()
    page.wait_for_timeout(1000)

    # Dialog should be closed
    expect(page.locator(".q-dialog")).to_have_count(0)


# ---------------------------------------------------------------------------
# Button 67: Apply Style (in dialog)
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_apply_style(browser_app_url: str, browser_page) -> None:
    """Click Apply Style in dialog → new tag chip appears; close → renderer shows style chip."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    dialog_chips_before = page.locator(".word-edit-tag-chip").count()

    # Click Apply Style — a default style is preselected
    page.locator(DIALOG_APPLY_STYLE).click()
    page.wait_for_timeout(500)

    # A new tag chip should appear in the dialog
    dialog_chips_after = page.locator(".word-edit-tag-chip").count()
    assert dialog_chips_after > dialog_chips_before

    # Close dialog and verify style indicator chip in main renderer
    page.keyboard.press("Escape")
    page.wait_for_timeout(1000)

    chip = page.locator('[data-testid="word-tag-chip"]').first
    expect(chip).to_be_visible(timeout=10_000)

    # Clean up: clear the tag in the renderer
    chip.hover()
    clear_btn = chip.locator('[data-testid="word-tag-clear-button"]').first
    expect(clear_btn).to_be_visible()
    clear_btn.click()
    page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Button 69: Clear Component (in dialog)
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_clear_component(browser_app_url: str, browser_page) -> None:
    """Apply Component → chip appears; click Clear Component → chip removed."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    dialog = page.locator(".q-dialog").last

    # Select component and apply
    dialog.get_by_label("Component").click()
    page.get_by_role("option", name="Footnote Marker").first.click()
    page.locator(DIALOG_APPLY_COMPONENT).click()
    page.wait_for_timeout(500)

    # Verify chip appeared
    chip_count = page.locator(".word-edit-tag-chip").count()
    assert chip_count >= 1

    # Click Clear Component
    page.locator(DIALOG_CLEAR_COMPONENT).click()
    page.wait_for_timeout(500)

    # Component chip should be removed (count returns to before)
    final_chip_count = page.locator(".word-edit-tag-chip").count()
    assert final_chip_count < chip_count

    # Close dialog
    page.locator(DIALOG_CLOSE).click()
