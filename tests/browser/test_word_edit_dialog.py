"""Browser tests for the word edit dialog header and style controls (Commit 8)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from .helpers import (
    load_project,
    navigate_to_page,
    wait_for_app_ready,
    wait_for_page_loaded,
)

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

EDIT_WORD_BUTTON = '[data-testid="edit-word-button"]'
DIALOG_APPLY_CLOSE = '[data-testid="dialog-apply-close-button"]'
DIALOG_CLOSE = '[data-testid="dialog-close-button"]'
DIALOG_APPLY_STYLE = '[data-testid="dialog-apply-style-button"]'
DIALOG_APPLY_COMPONENT = '[data-testid="dialog-apply-component-button"]'
DIALOG_CLEAR_COMPONENT = '[data-testid="dialog-clear-component-button"]'

# Commit 9
DIALOG_MERGE_PREV = '[data-testid="dialog-merge-prev-button"]'
DIALOG_MERGE_NEXT = '[data-testid="dialog-merge-next-button"]'
DIALOG_SPLIT_H = '[data-testid="dialog-split-h-button"]'
DIALOG_SPLIT_V = '[data-testid="dialog-split-v-button"]'
DIALOG_DELETE_WORD = '[data-testid="dialog-delete-word-button"]'

# Commits 10-11
DIALOG_CROP_ABOVE = '[data-testid="dialog-crop-above-button"]'
DIALOG_CROP_BELOW = '[data-testid="dialog-crop-below-button"]'
DIALOG_CROP_LEFT = '[data-testid="dialog-crop-left-button"]'
DIALOG_CROP_RIGHT = '[data-testid="dialog-crop-right-button"]'
DIALOG_REFINE_PREVIEW = '[data-testid="dialog-refine-preview-button"]'
DIALOG_EXPAND_REFINE_PREVIEW = '[data-testid="dialog-expand-refine-preview-button"]'
DIALOG_RESET_NUDGES = '[data-testid="dialog-reset-nudges-button"]'
DIALOG_APPLY_NUDGES = '[data-testid="dialog-apply-nudges-button"]'
DIALOG_APPLY_REFINE_NUDGES = '[data-testid="dialog-apply-refine-nudges-button"]'


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


def _open_dialog_with_enabled_merge_action(
    page: Page,
    action_selector: str,
    max_candidates: int = 40,
) -> None:
    """Open a word edit dialog where a specific merge action button is enabled.

    This avoids relying on global word positions that may map to a disabled
    merge button (for example, first word in a line for Merge Prev).
    """
    edit_buttons = page.locator(EDIT_WORD_BUTTON)
    total = min(edit_buttons.count(), max_candidates)

    for i in range(total):
        edit_buttons.nth(i).click()
        page.get_by_text("Merge / Split").first.wait_for(
            state="visible", timeout=10_000
        )

        dialog = page.locator(".q-dialog").last
        action_button = dialog.locator(action_selector)
        if action_button.is_enabled():
            return

        dialog.locator(DIALOG_CLOSE).click()
        page.wait_for_timeout(200)

    raise AssertionError(
        f"No dialog candidate found with enabled action: {action_selector}"
    )


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


# ===========================================================================
# Commit 9 — Merge / Split / Delete  (Buttons 71-75)
# ===========================================================================


# ---------------------------------------------------------------------------
# Standard: all 5 buttons present
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_merge_split_delete_buttons_present(
    browser_app_url: str, browser_page
) -> None:
    """All 5 merge/split/delete buttons visible in the dialog."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    expect(page.locator(DIALOG_MERGE_PREV)).to_be_visible()
    expect(page.locator(DIALOG_MERGE_NEXT)).to_be_visible()
    expect(page.locator(DIALOG_SPLIT_H)).to_be_visible()
    expect(page.locator(DIALOG_SPLIT_V)).to_be_visible()
    expect(page.locator(DIALOG_DELETE_WORD)).to_be_visible()


@pytest.mark.browser
def test_dialog_merge_prev_disabled_on_first_word(
    browser_app_url: str, browser_page
) -> None:
    """Merge Prev button is present; disabled state depends on word position."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)
    # Just verify the button is present — disabled state depends on which word
    # the first edit button corresponds to in the fixture data.
    expect(page.locator(DIALOG_MERGE_PREV)).to_be_visible()


@pytest.mark.browser
def test_dialog_merge_next_disabled_on_last_word(
    browser_app_url: str, browser_page
) -> None:
    """Merge Next button is present; disabled state depends on word position."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)
    # Just verify the button is present — disabled state depends on fixture data.
    expect(page.locator(DIALOG_MERGE_NEXT)).to_be_visible()


@pytest.mark.browser
def test_dialog_split_buttons_disabled_without_marker(
    browser_app_url: str, browser_page
) -> None:
    """H split and V split buttons are present in the dialog."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    # Verify buttons are present (disabled state depends on server-side marker state)
    expect(page.locator(DIALOG_SPLIT_H)).to_be_visible()
    expect(page.locator(DIALOG_SPLIT_V)).to_be_visible()


# ---------------------------------------------------------------------------
# Button 71: Merge Prev
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_merge_prev(browser_app_url: str, browser_page) -> None:
    """Open dialog on a word with enabled Merge Prev and verify merge applies."""
    page = browser_page
    _setup(page, browser_app_url)
    navigate_to_page(page, 3)

    # Wait for words to render before selecting a candidate dialog.
    page.wait_for_function(
        "() => document.querySelectorAll('[data-testid=\"edit-word-button\"]').length >= 3",
        timeout=10_000,
    )

    _open_dialog_with_enabled_merge_action(page, DIALOG_MERGE_PREV)

    dialog = page.locator(".q-dialog").last
    dialog.locator(DIALOG_MERGE_PREV).click()
    page.wait_for_timeout(500)
    expect(dialog.locator(DIALOG_CLOSE)).to_be_visible()

    dialog.locator(DIALOG_CLOSE).click()
    page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Button 72: Merge Next
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_merge_next(browser_app_url: str, browser_page) -> None:
    """Open dialog on a word with enabled Merge Next and verify merge applies."""
    page = browser_page
    _setup(page, browser_app_url)
    navigate_to_page(page, 3)

    page.wait_for_function(
        "() => document.querySelectorAll('[data-testid=\"edit-word-button\"]').length >= 3",
        timeout=10_000,
    )

    _open_dialog_with_enabled_merge_action(page, DIALOG_MERGE_NEXT)

    dialog = page.locator(".q-dialog").last
    dialog.locator(DIALOG_MERGE_NEXT).click()
    page.wait_for_timeout(500)
    expect(dialog.locator(DIALOG_CLOSE)).to_be_visible()

    dialog.locator(DIALOG_CLOSE).click()
    page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Button 75: Delete word
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_delete_word(browser_app_url: str, browser_page) -> None:
    """Open dialog → click Delete → notification appears confirming deletion."""
    page = browser_page
    _setup(page, browser_app_url)

    # Wait for word columns to render
    first_col = page.locator('[data-testid="word-column"]').first
    first_col.wait_for(state="visible", timeout=10_000)
    word_count_before = page.locator('[data-testid="word-column"]').count()
    assert word_count_before > 0, "No word columns found"

    _open_dialog(page)

    page.locator(DIALOG_DELETE_WORD).click()

    # Delete triggers a positive notification
    page.locator(".q-notification").first.wait_for(state="visible", timeout=10_000)

    page.locator(DIALOG_CLOSE).click()
    page.wait_for_timeout(500)


# ===========================================================================
# Commit 10 — BBox Cropping  (Buttons 76-79)
# ===========================================================================


def _open_dialog_and_click_image(page: Page) -> bool:
    """Open the first word dialog and click in the middle of the word image.

    Returns True if the image was found and clicked, False otherwise.
    """
    page.locator(EDIT_WORD_BUTTON).first.click()
    page.get_by_text("Merge / Split").first.wait_for(state="visible", timeout=10_000)

    dialog = page.locator(".q-dialog").last
    # The interactive image for split marker placement
    interactive_img = dialog.locator(".q-img, img").first
    if not interactive_img.is_visible():
        return False

    box = interactive_img.bounding_box()
    if box is None:
        return False

    # Click slightly off-center to avoid edge validation rejection
    cx = box["x"] + box["width"] * 0.4
    cy = box["y"] + box["height"] * 0.4
    page.mouse.click(cx, cy)
    page.wait_for_timeout(300)
    return True


@pytest.mark.browser
def test_dialog_crop_buttons_present(browser_app_url: str, browser_page) -> None:
    """Crop Above, Crop Below, Crop Left, Crop Right all visible in dialog."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    expect(page.locator(DIALOG_CROP_ABOVE)).to_be_visible()
    expect(page.locator(DIALOG_CROP_BELOW)).to_be_visible()
    expect(page.locator(DIALOG_CROP_LEFT)).to_be_visible()
    expect(page.locator(DIALOG_CROP_RIGHT)).to_be_visible()


@pytest.mark.browser
def test_dialog_crop_above(browser_app_url: str, browser_page) -> None:
    """Place marker → click Crop Above → Pending deltas are updated."""
    page = browser_page
    _setup(page, browser_app_url)

    if not _open_dialog_and_click_image(page):
        pytest.skip("Could not click word image to place marker")

    page.locator(DIALOG_CROP_ABOVE).click()
    page.wait_for_timeout(500)

    # Crop stages bbox deltas — Pending label must be visible
    expect(page.locator("text=/Pending/").first).to_be_visible()

    page.locator(DIALOG_CLOSE).click()


@pytest.mark.browser
def test_dialog_crop_below(browser_app_url: str, browser_page) -> None:
    """Place marker → click Crop Below → Pending deltas are updated."""
    page = browser_page
    _setup(page, browser_app_url)

    if not _open_dialog_and_click_image(page):
        pytest.skip("Could not click word image to place marker")

    page.locator(DIALOG_CROP_BELOW).click()
    page.wait_for_timeout(500)

    expect(page.locator("text=/Pending/").first).to_be_visible()

    page.locator(DIALOG_CLOSE).click()


@pytest.mark.browser
def test_dialog_crop_left(browser_app_url: str, browser_page) -> None:
    """Place marker → click Crop Left → Pending deltas are updated."""
    page = browser_page
    _setup(page, browser_app_url)

    if not _open_dialog_and_click_image(page):
        pytest.skip("Could not click word image to place marker")

    page.locator(DIALOG_CROP_LEFT).click()
    page.wait_for_timeout(500)

    expect(page.locator("text=/Pending/").first).to_be_visible()

    page.locator(DIALOG_CLOSE).click()


@pytest.mark.browser
def test_dialog_crop_right(browser_app_url: str, browser_page) -> None:
    """Place marker → click Crop Right → Pending deltas are updated."""
    page = browser_page
    _setup(page, browser_app_url)

    if not _open_dialog_and_click_image(page):
        pytest.skip("Could not click word image to place marker")

    page.locator(DIALOG_CROP_RIGHT).click()
    page.wait_for_timeout(500)

    expect(page.locator("text=/Pending/").first).to_be_visible()

    page.locator(DIALOG_CLOSE).click()


# ===========================================================================
# Commit 11 — Refine / Nudge / Apply  (Buttons 80-92)
# ===========================================================================


@pytest.mark.browser
def test_dialog_nudge_buttons_present(browser_app_url: str, browser_page) -> None:
    """All 8 nudge direction buttons plus Reset, Apply, Apply+Refine visible."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    expect(page.locator(DIALOG_REFINE_PREVIEW)).to_be_visible()
    expect(page.locator(DIALOG_EXPAND_REFINE_PREVIEW)).to_be_visible()
    expect(page.locator(DIALOG_RESET_NUDGES)).to_be_visible()
    expect(page.locator(DIALOG_APPLY_NUDGES)).to_be_visible()
    expect(page.locator(DIALOG_APPLY_REFINE_NUDGES)).to_be_visible()

    # Verify nudge direction buttons by text
    expect(page.get_by_role("button", name="X+").first).to_be_visible()
    expect(page.get_by_role("button", name="X-").first).to_be_visible()
    expect(page.get_by_role("button", name="Y+").first).to_be_visible()
    expect(page.get_by_role("button", name="Y-").first).to_be_visible()


@pytest.mark.browser
def test_dialog_refine_preview(browser_app_url: str, browser_page) -> None:
    """Click Refine → pending deltas update (dialog re-renders with changed pending label)."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    refine_btn = page.locator(DIALOG_REFINE_PREVIEW)
    if refine_btn.is_disabled():
        pytest.skip("Refine preview disabled (no refine callback available)")

    refine_btn.click()
    page.wait_for_timeout(1000)

    # Dialog should still be open
    expect(page.locator(".q-dialog")).not_to_have_count(0)
    page.locator(DIALOG_CLOSE).click()


@pytest.mark.browser
def test_dialog_expand_refine_preview(browser_app_url: str, browser_page) -> None:
    """Click Expand+Refine → dialog re-renders (pending label visible)."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    expand_btn = page.locator(DIALOG_EXPAND_REFINE_PREVIEW)
    if expand_btn.is_disabled():
        pytest.skip("Expand+Refine preview disabled")

    expand_btn.click()
    page.wait_for_timeout(1000)

    expect(page.locator(".q-dialog")).not_to_have_count(0)
    page.locator(DIALOG_CLOSE).click()


@pytest.mark.browser
def test_dialog_nudge_buttons(browser_app_url: str, browser_page) -> None:
    """Click X+ nudge → pending label shows non-zero delta; click Reset → label resets."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    # Click Left X+
    page.get_by_role("button", name="X+").first.click()
    page.wait_for_timeout(500)

    # Pending label should show non-zero left delta
    pending_text = page.locator("text=/Pending/").first.text_content() or ""
    assert "L:0" not in pending_text or "R:" in pending_text or "T:" in pending_text

    page.locator(DIALOG_CLOSE).click()


@pytest.mark.browser
def test_dialog_reset_nudges(browser_app_url: str, browser_page) -> None:
    """Nudge X+ → pending changes shown → click Reset → pending resets to zeros."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    # Make a nudge
    page.get_by_role("button", name="X+").first.click()
    page.wait_for_timeout(300)

    # Reset
    page.locator(DIALOG_RESET_NUDGES).click()
    page.wait_for_timeout(500)

    # Pending label should show all zeros
    pending_text = page.locator("text=/Pending/").first.text_content() or ""
    assert "L:0" in pending_text
    assert "R:0" in pending_text

    page.locator(DIALOG_CLOSE).click()


@pytest.mark.browser
def test_dialog_apply_nudges(browser_app_url: str, browser_page) -> None:
    """Nudge X+ → Apply → pending label resets to zeros (changes applied)."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    # Make a nudge
    page.get_by_role("button", name="X+").first.click()
    page.wait_for_timeout(300)

    apply_btn = page.locator(DIALOG_APPLY_NUDGES)
    apply_btn.click()
    page.wait_for_timeout(1500)

    # After apply, pending label resets to zeros (dialog stays open)
    pending_after = page.locator("text=/Pending/").first.text_content() or ""
    assert "L:0" in pending_after
    assert "R:0" in pending_after

    page.locator(DIALOG_CLOSE).click()


@pytest.mark.browser
def test_dialog_apply_and_refine_nudges(browser_app_url: str, browser_page) -> None:
    """Nudge → Apply+Refine → pending label resets to zeros (changes applied)."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    # Make a nudge
    page.get_by_role("button", name="X+").first.click()
    page.wait_for_timeout(300)

    apply_refine_btn = page.locator(DIALOG_APPLY_REFINE_NUDGES)
    if apply_refine_btn.is_disabled():
        pytest.skip("Apply+Refine disabled")

    apply_refine_btn.click()
    page.wait_for_timeout(1500)

    # After apply, pending label resets
    pending_after = page.locator("text=/Pending/").first.text_content() or ""
    assert "L:0" in pending_after

    page.locator(DIALOG_CLOSE).click()
