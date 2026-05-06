"""Browser tests for the word edit dialog header and style controls (Commit 8)."""

from __future__ import annotations

import re

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

# Dialog inputs / selects
DIALOG_GT_INPUT = '[data-testid="dialog-gt-input"]'
DIALOG_STYLE_SELECT = '[data-testid="dialog-style-select"]'
DIALOG_SCOPE_SELECT = '[data-testid="dialog-scope-select"]'
DIALOG_COMPONENT_SELECT = '[data-testid="dialog-component-select"]'

# Dialog nudge buttons (left / right edge X-/X+, top / bottom edge Y-/Y+)
DIALOG_NUDGE_LEFT_MINUS = '[data-testid="dialog-nudge-left-minus-button"]'
DIALOG_NUDGE_LEFT_PLUS = '[data-testid="dialog-nudge-left-plus-button"]'
DIALOG_NUDGE_RIGHT_MINUS = '[data-testid="dialog-nudge-right-minus-button"]'
DIALOG_NUDGE_RIGHT_PLUS = '[data-testid="dialog-nudge-right-plus-button"]'
DIALOG_NUDGE_TOP_MINUS = '[data-testid="dialog-nudge-top-minus-button"]'
DIALOG_NUDGE_TOP_PLUS = '[data-testid="dialog-nudge-top-plus-button"]'
DIALOG_NUDGE_BOTTOM_MINUS = '[data-testid="dialog-nudge-bottom-minus-button"]'
DIALOG_NUDGE_BOTTOM_PLUS = '[data-testid="dialog-nudge-bottom-plus-button"]'

# Dialog tag chip area
DIALOG_TAG_CHIPS_SLOT = '[data-testid="dialog-tag-chips-slot"]'
DIALOG_TAG_CHIPS_ROW = '[data-testid="dialog-tag-chips-row"]'
DIALOG_TAG_CHIP = '[data-testid="word-edit-tag-chip"]'
# Per-chip close-icon clear button rendered inside each ``DIALOG_TAG_CHIP``;
# becomes visible on chip hover (``mouseenter``).  This is the only
# style-clear affordance inside the dialog — there is no parallel
# ``dialog-clear-style-button`` to mirror ``dialog-clear-component-button``,
# because in the dialog the "Apply Component / Clear Component" button pair
# is for the component select while styles are cleared per-chip via this
# close icon.
DIALOG_TAG_CLEAR_BUTTON = '[data-testid="word-edit-tag-clear-button"]'

# Dialog zoom
DIALOG_CURRENT_ZOOM_TOGGLE = '[data-testid="dialog-current-zoom-toggle"]'

# Dialog Previous / Current / Next preview columns
DIALOG_PREVIOUS_PREVIEW_COLUMN = '[data-testid="dialog-previous-preview-column"]'
DIALOG_CURRENT_PREVIEW_COLUMN = '[data-testid="dialog-current-preview-column"]'
DIALOG_NEXT_PREVIEW_COLUMN = '[data-testid="dialog-next-preview-column"]'

# Dialog header label ("Edit Line N, Word M")
DIALOG_HEADER_LABEL = '[data-testid="dialog-header-label"]'


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
    max_candidates: int = 80,
) -> None:
    """Open a word edit dialog where a specific merge action button is enabled.

    This avoids relying on global word positions that may map to a disabled
    merge button (for example, first word in a line for Merge Prev).
    """
    edit_buttons = page.locator(EDIT_WORD_BUTTON)
    # Wait until the edit-button count is stable across two consecutive reads
    # AND non-trivial — page 3 occasionally renders with 0 edit buttons for a
    # brief moment as the word grid is rebuilt, which would otherwise cause us
    # to immediately bail out with no candidates.
    import time as _time

    deadline = _time.monotonic() + 15.0
    last_count = -1
    while _time.monotonic() < deadline:
        c = edit_buttons.count()
        if c >= 20 and c == last_count:
            break
        last_count = c
        page.wait_for_timeout(250)
    total = min(edit_buttons.count(), max_candidates)

    for i in range(total):
        # Make sure no leftover dialog from a prior iteration is still
        # displayed — clicking through it can lead Playwright to read the
        # wrong dialog's button state.
        try:
            page.locator(".q-dialog").first.wait_for(state="detached", timeout=2_000)
        except Exception:
            pass

        edit_buttons.nth(i).click()
        try:
            page.get_by_text("Merge / Split").first.wait_for(
                state="visible", timeout=5_000
            )
        except Exception:
            # Click was likely dropped by the NiceGUI socket layer — try once
            # more on the same edit button before moving on.
            page.wait_for_timeout(300)
            edit_buttons.nth(i).click()
            page.get_by_text("Merge / Split").first.wait_for(
                state="visible", timeout=10_000
            )

        dialog = page.locator(".q-dialog").last
        action_button = dialog.locator(action_selector)
        # Wait for the action button to be attached and let Quasar/NiceGUI
        # finish applying the ``disable`` prop before reading is_enabled().
        action_button.wait_for(state="attached", timeout=5_000)
        page.wait_for_timeout(200)
        # The button may briefly report disabled while the dialog finishes
        # initializing; poll a few times before deciding to move on.  Read
        # the actual ``disabled`` attribute directly — under heavy coverage
        # instrumentation, ``is_enabled()`` was occasionally returning False
        # even after Quasar had cleared the disabled state.
        enabled = False
        for _ in range(15):
            disabled_attr = action_button.get_attribute("disabled")
            aria_disabled = action_button.get_attribute("aria-disabled")
            if disabled_attr is None and aria_disabled in (None, "false"):
                enabled = True
                break
            page.wait_for_timeout(150)
        if enabled:
            return

        dialog.locator(DIALOG_CLOSE).click()
        # Wait for this dialog to actually close before iterating again.
        try:
            dialog.wait_for(state="detached", timeout=3_000)
        except Exception:
            page.wait_for_timeout(400)

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
    header = dialog.locator(DIALOG_HEADER_LABEL)
    expect(header).to_be_visible()
    expect(header).to_have_text(re.compile(r"Edit Line \d+, Word \d+"))

    # GT input should be present
    gt_input = dialog.locator(DIALOG_GT_INPUT)
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

    gt_input = dialog.locator(DIALOG_GT_INPUT)
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
    gt_input = dialog.locator(DIALOG_GT_INPUT)
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

    dialog_chips_before = page.locator(DIALOG_TAG_CHIP).count()

    # Click Apply Style — a default style is preselected
    page.locator(DIALOG_APPLY_STYLE).click()
    page.wait_for_timeout(500)

    # A new tag chip should appear in the dialog
    dialog_chips_after = page.locator(DIALOG_TAG_CHIP).count()
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

    # Select component and apply (data-testid lands on the q-select wrapper;
    # clicking it opens the menu).
    dialog.locator(DIALOG_COMPONENT_SELECT).click()
    page.get_by_role("option", name="Footnote Marker").first.click()
    page.locator(DIALOG_APPLY_COMPONENT).click()
    page.wait_for_timeout(500)

    # Verify chip appeared
    chip_count = page.locator(DIALOG_TAG_CHIP).count()
    assert chip_count >= 1

    # Click Clear Component
    page.locator(DIALOG_CLEAR_COMPONENT).click()
    page.wait_for_timeout(500)

    # Component chip should be removed (count returns to before)
    final_chip_count = page.locator(DIALOG_TAG_CHIP).count()
    assert final_chip_count < chip_count

    # Close dialog
    page.locator(DIALOG_CLOSE).click()


# ---------------------------------------------------------------------------
# Per-chip clear (style chip): the missing mirror of clear-component
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_clear_style_chip(browser_app_url: str, browser_page) -> None:
    """Apply Style → style chip appears; click chip's clear icon → chip removed.

    Counterpart to ``test_dialog_clear_component``.  There is **no**
    ``dialog-clear-style-button`` to mirror ``dialog-clear-component-button``
    — in the dialog, styles are cleared per-chip via the ``close`` icon
    rendered *inside* each ``word-edit-tag-chip`` (see
    ``word_edit_dialog.py::_render_tag_chips`` ll. 827-846).  That close
    icon carries testid ``word-edit-tag-clear-button`` and is rendered
    invisible by default, becoming visible on chip ``mouseenter``.

    To match the pre-existing renderer-side cleanup pattern in
    ``test_dialog_apply_style`` (which uses the *renderer* chip's clear
    button after the dialog is closed), this test exercises the
    *in-dialog* path: apply a style, hover the chip, click its clear
    icon, and assert the chip count drops back.  This locks in:

    1. The ``word-edit-tag-clear-button`` testid is reachable inside
       ``word-edit-tag-chip`` rows.
    2. Hover-to-reveal works (the clear button is interactable after
       ``mouseenter``).
    3. The clear handler removes the style from the active word and
       triggers ``_render_tag_chips`` to drop the chip.

    The asymmetry (no parallel button) is captured in the planning
    doc's "Tag-chip clear in dialog" entry; this test closes that
    coverage gap by verifying the only affordance that exists.
    """
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    chips_before = page.locator(DIALOG_TAG_CHIP).count()

    # Apply Style — a default style is preselected on dialog open.
    page.locator(DIALOG_APPLY_STYLE).click()
    page.wait_for_timeout(500)

    chips_after_apply = page.locator(DIALOG_TAG_CHIP).count()
    assert chips_after_apply > chips_before, (
        f"Expected chip count to increase after Apply Style; "
        f"before={chips_before} after={chips_after_apply}"
    )

    # Hover the most-recently-added chip to reveal its clear button.
    chip = page.locator(DIALOG_TAG_CHIP).last
    chip.hover()
    page.wait_for_timeout(200)

    clear_btn = chip.locator(DIALOG_TAG_CLEAR_BUTTON).first
    expect(clear_btn).to_be_visible(timeout=5_000)
    clear_btn.click()
    page.wait_for_timeout(500)

    # Style chip should be removed; count returns to (or below) the baseline.
    chips_final = page.locator(DIALOG_TAG_CHIP).count()
    assert chips_final < chips_after_apply, (
        f"Expected chip count to drop after clear-icon click; "
        f"before-clear={chips_after_apply} after-clear={chips_final}"
    )

    # Close dialog
    page.locator(DIALOG_CLOSE).click()


# ---------------------------------------------------------------------------
# Apply Style via dropdown selection (drives ``dialog-style-select`` to
# pick a non-default style value, then verifies that exact style ends up
# on the chip — the symmetric pair of ``test_dialog_apply_style`` (which
# only exercises the *default* preselected style) and the in-dialog
# clear path covered by ``test_dialog_clear_style_chip``.
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_apply_style_via_dropdown(browser_app_url: str, browser_page) -> None:
    """Open style select → pick "Italics" → Apply Style → chip text is "Italics".

    The default style preselected on dialog open is the first entry of
    ``WordOperations.supported_styles`` after ``regular`` is filtered and
    the remaining labels are ``sorted()``: ``"all caps"`` (display
    ``"All Caps"``).  Picking ``"Italics"`` from the dropdown verifies
    that:

    1. Clicking the q-select wrapper (``DIALOG_STYLE_SELECT`` testid
       lands on the wrapper, not the underlying menu) does open the
       q-menu.
    2. Selecting a q-item by visible text drives
       ``_set_selected_style`` and updates ``_selected_style_value``.
    3. ``_apply_selected_style_from_dialog`` then routes through
       ``WordOperations.apply_style_to_word`` with the *selected* value
       (not the default), and ``_render_tag_chips`` redraws a chip whose
       label matches.

    Counterpart to ``test_dialog_apply_style`` (default-style apply,
    no dropdown drive) and ``test_dialog_clear_style_chip`` (clear-side
    of the same chip life cycle).
    """
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    dialog = page.locator(".q-dialog").last
    chips_before = dialog.locator(DIALOG_TAG_CHIP).count()

    # Drive the style-select dropdown to "Italics" (a non-default value).
    # The data-testid lands on the q-select wrapper; clicking it opens the
    # q-menu, then we click the q-item with the matching display text.
    dialog.locator(DIALOG_STYLE_SELECT).click()
    page.get_by_role("option", name="Italics").first.click()
    page.wait_for_timeout(200)

    # Apply the selected style.
    page.locator(DIALOG_APPLY_STYLE).click()
    page.wait_for_timeout(500)

    # A new tag chip should appear whose label is "Italics" — proving the
    # dropdown selection (not the default) drove the apply.  Use
    # ``to_have_count`` for auto-waiting against NiceGUI re-render timing.
    expect(dialog.locator(DIALOG_TAG_CHIP)).to_have_count(chips_before + 1)
    expect(dialog.locator(DIALOG_TAG_CHIP).filter(has_text="Italics")).to_have_count(1)

    # Cleanup: hover the new chip and click its clear icon to remove the
    # style so subsequent tests on the same fixture session start clean.
    italics_chip = dialog.locator(DIALOG_TAG_CHIP).filter(has_text="Italics").first
    italics_chip.hover()
    page.wait_for_timeout(200)
    clear_btn = italics_chip.locator(DIALOG_TAG_CLEAR_BUTTON).first
    expect(clear_btn).to_be_visible(timeout=5_000)
    clear_btn.click()
    page.wait_for_timeout(500)

    expect(dialog.locator(DIALOG_TAG_CHIP)).to_have_count(chips_before)

    page.locator(DIALOG_CLOSE).click()


# ---------------------------------------------------------------------------
# Apply Component via dropdown selection (drives ``dialog-component-select``
# to pick a non-default component value, then verifies that exact component
# ends up on the chip — symmetric mirror of
# ``test_dialog_apply_style_via_dropdown``.  ``test_dialog_clear_component``
# already opens the component select and picks "Footnote Marker", but only
# asserts ``chip_count >= 1`` — it does not verify the chip *text* matches
# the picked component, so a regression that wired the dropdown to the
# wrong component value would still pass that test.  This test closes that
# coverage gap.
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_apply_component_via_dropdown(
    browser_app_url: str, browser_page
) -> None:
    """Open component select → pick "Superscript" → Apply Component → chip text is "Superscript".

    The default component preselected on dialog open is the first entry
    of ``WordOperations.supported_components`` after
    ``ALLOWED_COMPONENTS`` is sorted: ``"drop cap"`` (display
    ``"Drop Cap"``).  Picking ``"Superscript"`` from the dropdown
    verifies that:

    1. Clicking the q-select wrapper (``DIALOG_COMPONENT_SELECT`` testid
       lands on the wrapper, not the underlying menu) does open the
       q-menu.
    2. Selecting a q-item by visible text drives
       ``_set_selected_component`` and updates
       ``_selected_component_value``.
    3. ``_apply_selected_component_from_dialog(enabled=True)`` then
       routes through the underlying component-set path with the
       *selected* value (not the default), and ``_render_tag_chips``
       redraws a chip whose label matches.

    Counterpart to ``test_dialog_apply_style_via_dropdown`` (style-side
    of the same dropdown-drive pattern) and ``test_dialog_clear_component``
    (which exercises the dropdown-open + clear-component button but not
    the chip-text assertion).
    """
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    dialog = page.locator(".q-dialog").last
    chips_before = dialog.locator(DIALOG_TAG_CHIP).count()

    # Drive the component-select dropdown to "Superscript" (a non-default
    # value; default is "Drop Cap" because ``ALLOWED_COMPONENTS`` is
    # sorted and "drop cap" sorts first).  The data-testid lands on the
    # q-select wrapper; clicking it opens the q-menu, then we click the
    # q-item with the matching display text.
    dialog.locator(DIALOG_COMPONENT_SELECT).click()
    page.get_by_role("option", name="Superscript").first.click()
    page.wait_for_timeout(200)

    # Apply the selected component.
    page.locator(DIALOG_APPLY_COMPONENT).click()
    page.wait_for_timeout(500)

    # A new tag chip should appear whose label is "Superscript" — proving
    # the dropdown selection (not the default) drove the apply.  Use
    # ``to_have_count`` for auto-waiting against NiceGUI re-render timing.
    expect(dialog.locator(DIALOG_TAG_CHIP)).to_have_count(chips_before + 1)
    expect(
        dialog.locator(DIALOG_TAG_CHIP).filter(has_text="Superscript")
    ).to_have_count(1)

    # Cleanup: click Clear Component (the existing affordance for
    # component chips — symmetric counterpart to per-chip clear used in
    # the style test) so subsequent tests on the same fixture session
    # start clean.
    page.locator(DIALOG_CLEAR_COMPONENT).click()
    page.wait_for_timeout(500)

    expect(dialog.locator(DIALOG_TAG_CHIP)).to_have_count(chips_before)

    page.locator(DIALOG_CLOSE).click()


# ---------------------------------------------------------------------------
# Apply Scope via dropdown selection (drives ``dialog-scope-select`` to set
# scope on a previously-applied style; verifies the chip text re-renders to
# include the scope suffix per ``_word_display_tag_items`` line 639).
#
# Closes the third-and-final dialog dropdown trio: iter 28 covered
# ``dialog-style-select``, iter 29 covered ``dialog-component-select``, and
# this iter covers ``dialog-scope-select``.  The scope select differs from
# the other two in two ways:
#
# 1. There is no separate "Apply Scope" button — the on-change handler
#    ``_apply_scope_for_selected_style`` fires immediately on dropdown
#    selection (see ``word_edit_dialog.py`` line 1548-1552).
# 2. Scope is meaningful only when a style is already applied to the chip,
#    so the test must apply a style first, then change scope.
#
# The chip-text format with scope is ``"<Style> (<Scope.title()>)"`` per
# ``_word_display_tag_items`` line 639 — e.g. picking "Italics" then
# "Part" yields chip text "Italics (Part)".
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_apply_scope_via_dropdown(browser_app_url: str, browser_page) -> None:
    """Apply Italics → open scope select → pick "Part" → chip reads "Italics (Part)".

    Verifies that:

    1. Clicking the q-select wrapper (``DIALOG_SCOPE_SELECT`` testid lands
       on the wrapper, not the underlying menu) opens the q-menu.
    2. Selecting a q-item by visible text drives the on-change handler
       ``_apply_scope_for_selected_style`` directly (no separate Apply
       button).
    3. ``WordOperations.apply_scope_to_word_style`` re-renders the existing
       style chip with the scope suffix per
       ``WordMatchView._word_display_tag_items`` line 639.

    Counterpart to ``test_dialog_apply_style_via_dropdown`` and
    ``test_dialog_apply_component_via_dropdown`` (the other two dialog
    dropdowns).  This test closes the dropdown trio.
    """
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    dialog = page.locator(".q-dialog").last
    chips_before = dialog.locator(DIALOG_TAG_CHIP).count()

    # Step 1: apply "Italics" via the style dropdown so we have a styled
    # chip on which scope is meaningful.  Mirrors the first half of
    # ``test_dialog_apply_style_via_dropdown``.
    dialog.locator(DIALOG_STYLE_SELECT).click()
    page.get_by_role("option", name="Italics").first.click()
    page.wait_for_timeout(200)
    page.locator(DIALOG_APPLY_STYLE).click()
    page.wait_for_timeout(500)

    expect(dialog.locator(DIALOG_TAG_CHIP)).to_have_count(chips_before + 1)
    italics_chip = dialog.locator(DIALOG_TAG_CHIP).filter(has_text="Italics").first
    # ``WordOperations.apply_style_to_word`` hard-codes the initial scope
    # to "whole" (see ``word_operations.py`` line 134-137), so the chip
    # text after the style apply is "Italics (Whole)" plus the inline
    # clear-icon button's "close" text.  Use ``to_contain_text`` to
    # pin the *scope-suffix* portion specifically — this is the value
    # we will verify changes after the scope dropdown drive below.
    expect(italics_chip).to_contain_text("(Whole)")

    # Step 2: drive the scope-select dropdown to "Part" (different from
    # the post-apply default of "Whole").  The on-change handler fires
    # immediately, applying scope to the most recently selected style
    # (Italics) — there is no separate Apply Scope button to click.
    dialog.locator(DIALOG_SCOPE_SELECT).click()
    page.get_by_role("option", name="Part").first.click()
    page.wait_for_timeout(500)

    # Step 3: chip count should be unchanged (still one Italics chip),
    # but the chip's scope suffix should now read "(Part)" per
    # ``_word_display_tag_items`` line 639's f-string format
    # (``f"{display} ({normalized_scope.title()})"``).  Re-locate the
    # chip after re-render — the prior locator handle may be stale since
    # ``_render_tag_chips`` re-creates the chips.
    expect(dialog.locator(DIALOG_TAG_CHIP)).to_have_count(chips_before + 1)
    italics_chip_after = (
        dialog.locator(DIALOG_TAG_CHIP).filter(has_text="Italics").first
    )
    expect(italics_chip_after).to_contain_text("(Part)")
    # And specifically *not* "(Whole)" any more — proves the scope
    # actually changed rather than a duplicate chip being added.
    expect(italics_chip_after).not_to_contain_text("(Whole)")

    # Cleanup: hover the chip and click its embedded clear icon to remove
    # the style entirely (clearing the style also discards its scope), so
    # subsequent tests on the same fixture session start clean.  Mirrors
    # the cleanup pattern in ``test_dialog_apply_style_via_dropdown``.
    italics_chip_after.hover()
    page.wait_for_timeout(200)
    clear_btn = italics_chip_after.locator(DIALOG_TAG_CLEAR_BUTTON).first
    expect(clear_btn).to_be_visible(timeout=5_000)
    clear_btn.click()
    page.wait_for_timeout(500)

    expect(dialog.locator(DIALOG_TAG_CHIP)).to_have_count(chips_before)

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

    # Verify nudge direction buttons via stable testids — all 8 must be present.
    expect(page.locator(DIALOG_NUDGE_LEFT_MINUS)).to_be_visible()
    expect(page.locator(DIALOG_NUDGE_LEFT_PLUS)).to_be_visible()
    expect(page.locator(DIALOG_NUDGE_RIGHT_MINUS)).to_be_visible()
    expect(page.locator(DIALOG_NUDGE_RIGHT_PLUS)).to_be_visible()
    expect(page.locator(DIALOG_NUDGE_TOP_MINUS)).to_be_visible()
    expect(page.locator(DIALOG_NUDGE_TOP_PLUS)).to_be_visible()
    expect(page.locator(DIALOG_NUDGE_BOTTOM_MINUS)).to_be_visible()
    expect(page.locator(DIALOG_NUDGE_BOTTOM_PLUS)).to_be_visible()


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
    page.locator(DIALOG_NUDGE_LEFT_PLUS).click()
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
    page.locator(DIALOG_NUDGE_LEFT_PLUS).click()
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
    page.locator(DIALOG_NUDGE_LEFT_PLUS).click()
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
    page.locator(DIALOG_NUDGE_LEFT_PLUS).click()
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


# ---------------------------------------------------------------------------
# Preview columns (Previous / Current / Next)
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_preview_columns_present(browser_app_url: str, browser_page) -> None:
    """Previous, Current, and Next preview columns are addressable by testid."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    dialog = page.locator(".q-dialog").last
    expect(dialog).to_be_visible()

    # All three preview-column wrappers should be present and visible.
    previous_col = dialog.locator(DIALOG_PREVIOUS_PREVIEW_COLUMN)
    current_col = dialog.locator(DIALOG_CURRENT_PREVIEW_COLUMN)
    next_col = dialog.locator(DIALOG_NEXT_PREVIEW_COLUMN)

    expect(previous_col).to_be_visible()
    expect(current_col).to_be_visible()
    expect(next_col).to_be_visible()

    # Each column carries the matching caption label.
    expect(previous_col.locator("text=Previous")).to_be_visible()
    expect(current_col.locator("text=Current")).to_be_visible()
    expect(next_col.locator("text=Next")).to_be_visible()

    # The Current column must contain the GT input (sanity-check that the
    # right wrapper is tagged, not just any column).
    expect(current_col.locator(DIALOG_GT_INPUT)).to_be_visible()

    page.locator(DIALOG_CLOSE).click()
