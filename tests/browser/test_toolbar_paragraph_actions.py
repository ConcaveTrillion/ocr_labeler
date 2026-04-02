"""Browser tests for paragraph-scope toolbar action buttons."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

PARA_MERGE = '[data-testid="paragraph-merge-button"]'
PARA_REFINE = '[data-testid="paragraph-refine-bboxes-button"]'
PARA_EXPAND_REFINE = '[data-testid="paragraph-expand-refine-bboxes-button"]'
PARA_SPLIT_AFTER_LINE = '[data-testid="paragraph-split-after-line-button"]'
PARA_GT_TO_OCR = '[data-testid="paragraph-copy-gt-to-ocr-button"]'
PARA_OCR_TO_GT = '[data-testid="paragraph-copy-ocr-to-gt-button"]'
PARA_VALIDATE = '[data-testid="paragraph-validate-button"]'
PARA_UNVALIDATE = '[data-testid="paragraph-unvalidate-button"]'
PARA_DELETE = '[data-testid="paragraph-delete-button"]'

PARA_CHECKBOX = '[data-testid="paragraph-checkbox"]'
PARA_EXPANDER = '[data-testid="paragraph-expander-button"]'
LINE_DELETE = '[data-testid="line-delete-button"]'
WORD_VALIDATE_BUTTON = '[data-testid="word-validate-button"]'

ALL_PARA_BUTTONS = [
    PARA_MERGE,
    PARA_REFINE,
    PARA_EXPAND_REFINE,
    PARA_SPLIT_AFTER_LINE,
    PARA_GT_TO_OCR,
    PARA_OCR_TO_GT,
    PARA_VALIDATE,
    PARA_UNVALIDATE,
    PARA_DELETE,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(page: Page, url: str) -> None:
    """Navigate, load project, and wait for page content."""
    page.goto(url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)


def _switch_to_all_lines(page: Page) -> None:
    """Switch the filter toggle to 'All Lines' so all line cards render."""
    page.get_by_text("All Lines").first.click()
    page.wait_for_timeout(500)
    # Wait for paragraph expanders to render after filter change
    page.locator(PARA_EXPANDER).first.wait_for(state="visible", timeout=15_000)


def _wait_for_notification(page: Page, timeout: int = 15_000) -> None:
    """Wait for a Quasar notification to appear."""
    page.locator(".q-notification").first.wait_for(state="visible", timeout=timeout)


def _select_paragraph(page: Page, index: int = 0) -> None:
    """Check the Nth paragraph checkbox (0-based)."""
    checkboxes = page.locator(PARA_CHECKBOX)
    checkboxes.nth(index).wait_for(state="visible", timeout=10_000)
    checkboxes.nth(index).click()
    page.wait_for_timeout(1000)


def _get_gt_inputs(page: Page):
    """Return all GT input elements in the word match area."""
    return page.locator(".q-field--outlined input")


def _get_ocr_labels(page: Page):
    """Return OCR label elements."""
    return page.locator(".monospace:not(.q-field)")


# ---------------------------------------------------------------------------
# Presence / disabled-state tests
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_paragraph_scope_buttons_disabled_without_selection(
    browser_app_url: str, browser_page
) -> None:
    """All paragraph-scope buttons are disabled when nothing is selected."""
    page = browser_page
    _setup(page, browser_app_url)

    for selector in ALL_PARA_BUTTONS:
        btn = page.locator(selector)
        expect(btn).to_be_visible()
        expect(btn).to_be_disabled()


@pytest.mark.browser
def test_paragraph_scope_buttons_enabled_with_selection(
    browser_app_url: str, browser_page
) -> None:
    """Selecting a paragraph enables most paragraph-scope buttons."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_paragraph(page, 0)

    # Buttons that need 1+ paragraph selected should be enabled
    for selector in [
        PARA_REFINE,
        PARA_EXPAND_REFINE,
        PARA_GT_TO_OCR,
        PARA_OCR_TO_GT,
        PARA_VALIDATE,
        PARA_UNVALIDATE,
        PARA_DELETE,
    ]:
        expect(page.locator(selector)).to_be_enabled()

    # Merge needs 2+ paragraphs — should still be disabled
    expect(page.locator(PARA_MERGE)).to_be_disabled()


@pytest.mark.browser
def test_paragraph_scope_buttons_have_tooltips(
    browser_app_url: str, browser_page
) -> None:
    """Each paragraph-scope button has a descriptive tooltip on hover."""
    page = browser_page
    _setup(page, browser_app_url)

    buttons_tooltips = [
        (PARA_MERGE, "Merge selected paragraphs"),
        (PARA_REFINE, "Refine selected paragraphs"),
        (PARA_EXPAND_REFINE, "Expand then refine selected paragraphs"),
        (PARA_SPLIT_AFTER_LINE, "Split the containing paragraph"),
        (PARA_GT_TO_OCR, "Copy ground truth text to OCR"),
        (PARA_OCR_TO_GT, "Copy OCR text to ground truth"),
        (PARA_VALIDATE, "Validate all words in selected paragraphs"),
        (PARA_UNVALIDATE, "Unvalidate all words in selected paragraphs"),
        (PARA_DELETE, "Delete selected paragraphs"),
    ]

    for selector, expected_text in buttons_tooltips:
        btn = page.locator(selector)
        btn.hover()
        tooltip = page.get_by_role("tooltip").filter(has_text=expected_text)
        expect(tooltip).to_be_visible()
        page.mouse.move(0, 0)
        page.wait_for_timeout(300)


# ---------------------------------------------------------------------------
# Click / interaction tests
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_paragraph_refine(browser_app_url: str, browser_page) -> None:
    """Select paragraph, click Refine: success notification appears."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_paragraph(page, 0)
    page.locator(PARA_REFINE).click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_paragraph_expand_refine(browser_app_url: str, browser_page) -> None:
    """Select paragraph, click Expand+Refine: success notification appears."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_paragraph(page, 0)
    page.locator(PARA_EXPAND_REFINE).click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_paragraph_copy_gt_to_ocr(browser_app_url: str, browser_page) -> None:
    """Select paragraph, click GT→OCR: OCR labels update to match GT values."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    # Read first GT value before action
    gt_input = _get_gt_inputs(page).first
    expect(gt_input).to_be_visible()
    gt_value = gt_input.input_value()

    _select_paragraph(page, 0)
    page.locator(PARA_GT_TO_OCR).click()
    page.wait_for_timeout(1000)

    # First OCR label should now match the GT value
    ocr_label = _get_ocr_labels(page).first
    expect(ocr_label).to_have_text(gt_value)


@pytest.mark.browser
def test_paragraph_copy_ocr_to_gt(browser_app_url: str, browser_page) -> None:
    """Select paragraph, click OCR→GT: GT inputs update to match OCR labels."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    # Read first OCR label before action
    ocr_label = _get_ocr_labels(page).first
    expect(ocr_label).to_be_visible()
    ocr_value = ocr_label.text_content()

    _select_paragraph(page, 0)
    page.locator(PARA_OCR_TO_GT).click()
    page.wait_for_timeout(1000)

    # First GT input should now equal the OCR value
    gt_input = _get_gt_inputs(page).first
    expect(gt_input).to_have_value(ocr_value)


@pytest.mark.browser
def test_paragraph_validate(browser_app_url: str, browser_page) -> None:
    """Select paragraph, click Validate: word validate buttons turn green."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    page.locator(WORD_VALIDATE_BUTTON).first.wait_for(state="visible", timeout=15_000)

    _select_paragraph(page, 0)
    page.locator(PARA_VALIDATE).click()
    page.wait_for_timeout(1000)

    # Word validate buttons in the first paragraph should be green.
    # The first paragraph's words are the first few validate buttons.
    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-green"))


@pytest.mark.browser
def test_paragraph_unvalidate(browser_app_url: str, browser_page) -> None:
    """Validate paragraph first, then Unvalidate: buttons revert to grey."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    page.locator(WORD_VALIDATE_BUTTON).first.wait_for(state="visible", timeout=15_000)

    # Validate first
    _select_paragraph(page, 0)
    page.locator(PARA_VALIDATE).click()
    page.wait_for_timeout(1000)

    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-green"))

    # Now Unvalidate
    page.locator(PARA_UNVALIDATE).click()
    page.wait_for_timeout(1000)

    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-grey"))


@pytest.mark.browser
def test_paragraph_delete(browser_app_url: str, browser_page) -> None:
    """Select paragraph, click Delete: paragraph count decreases by 1."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    # Count paragraph expanders before
    expanders_before = page.locator(PARA_EXPANDER).count()
    assert expanders_before > 1, "Need at least 2 paragraphs for delete test"

    # Select the first paragraph (using checkbox count, which may differ from expanders)
    checkboxes = page.locator(PARA_CHECKBOX)
    checkbox_count = checkboxes.count()
    assert checkbox_count >= 1, "Need at least 1 paragraph checkbox"
    _select_paragraph(page, 0)

    # Verify delete button is enabled after selection
    delete_btn = page.locator(PARA_DELETE)
    expect(delete_btn).to_be_enabled()

    delete_btn.click()
    page.wait_for_timeout(1000)

    # Paragraph count should decrease by 1
    expect(page.locator(PARA_EXPANDER)).to_have_count(expanders_before - 1)


@pytest.mark.browser
def test_paragraph_merge(browser_app_url: str, browser_page) -> None:
    """Select 2 paragraphs, click Merge: paragraph count decreases by 1."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    expanders_before = page.locator(PARA_EXPANDER).count()
    assert expanders_before >= 2, "Need at least 2 paragraphs for merge test"

    # Count lines before merge
    lines_before = page.locator(LINE_DELETE).count()

    # Select two adjacent paragraphs — verify each selection takes effect
    _select_paragraph(page, 0)
    expect(page.locator(PARA_DELETE)).to_be_enabled()

    _select_paragraph(page, 1)

    # Merge should now be enabled (2 paragraphs selected)
    merge_btn = page.locator(PARA_MERGE)
    expect(merge_btn).to_be_enabled(timeout=10_000)

    merge_btn.click()
    page.wait_for_timeout(1000)

    # Paragraph count should decrease by 1
    expect(page.locator(PARA_EXPANDER)).to_have_count(expanders_before - 1)

    # Lines should be preserved (combined into one paragraph)
    expect(page.locator(LINE_DELETE)).to_have_count(lines_before)


@pytest.mark.browser
def test_paragraph_split_after_line(browser_app_url: str, browser_page) -> None:
    """Merge two paragraphs, then split: paragraph count returns to original."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    expanders_before = page.locator(PARA_EXPANDER).count()
    assert expanders_before >= 2, "Need at least 2 paragraphs for split test"

    # All fixture paragraphs have 1 line each, so we must first merge two
    # paragraphs to create a multi-line paragraph we can then split.
    _select_paragraph(page, 0)
    _select_paragraph(page, 1)
    merge_btn = page.locator(PARA_MERGE)
    expect(merge_btn).to_be_enabled(timeout=10_000)
    merge_btn.click()
    page.wait_for_timeout(1000)

    # After merge: one fewer paragraph, but a 2-line paragraph now exists
    expect(page.locator(PARA_EXPANDER)).to_have_count(expanders_before - 1)

    # Deselect paragraphs by clicking the checkboxes again
    checkboxes = page.locator(PARA_CHECKBOX)
    for i in range(checkboxes.count()):
        cb = checkboxes.nth(i)
        if cb.is_checked():
            cb.click()
            page.wait_for_timeout(300)

    # Select the first line of the merged paragraph (first line checkbox).
    # This is the first line of a 2-line paragraph, so split should succeed.
    line_checkboxes = page.get_by_label("Select line", exact=True)
    assert line_checkboxes.count() >= 2, "Need at least 2 lines for split test"
    line_checkboxes.first.click()
    page.wait_for_timeout(1000)

    split_btn = page.locator(PARA_SPLIT_AFTER_LINE)
    expect(split_btn).to_be_enabled(timeout=10_000)
    split_btn.click()
    page.wait_for_timeout(1000)

    # Notification should confirm success (not failure)
    notification = page.locator(".q-notification").first
    notification.wait_for(state="visible", timeout=15_000)
    expect(notification).to_contain_text("Split paragraph after line")

    # Paragraph count should return to the original (merge -1, then split +1)
    expect(page.locator(PARA_EXPANDER)).to_have_count(expanders_before)
