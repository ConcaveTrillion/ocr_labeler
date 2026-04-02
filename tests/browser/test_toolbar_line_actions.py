"""Browser tests for line-scope toolbar action buttons."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

LINE_MERGE = '[data-testid="line-merge-button"]'
LINE_REFINE = '[data-testid="line-refine-bboxes-button"]'
LINE_EXPAND_REFINE = '[data-testid="line-expand-refine-bboxes-button"]'
LINE_SPLIT_AFTER_WORD = '[data-testid="line-split-after-word-button"]'
LINE_SPLIT_BY_SELECTION = '[data-testid="line-split-by-selection-button"]'
LINE_FORM_PARAGRAPH = '[data-testid="line-form-paragraph-button"]'
LINE_GT_TO_OCR = '[data-testid="line-copy-gt-to-ocr-toolbar-button"]'
LINE_OCR_TO_GT = '[data-testid="line-copy-ocr-to-gt-toolbar-button"]'
LINE_VALIDATE = '[data-testid="line-validate-toolbar-button"]'
LINE_UNVALIDATE = '[data-testid="line-unvalidate-toolbar-button"]'
LINE_DELETE = '[data-testid="line-delete-toolbar-button"]'

# Per-line card delete button (used to count lines)
LINE_DELETE_CARD = '[data-testid="line-delete-button"]'
PARA_EXPANDER = '[data-testid="paragraph-expander-button"]'
WORD_VALIDATE_BUTTON = '[data-testid="word-validate-button"]'
WORD_CHECKBOX = '[data-testid="word-checkbox"]'

ALL_LINE_BUTTONS = [
    LINE_MERGE,
    LINE_REFINE,
    LINE_EXPAND_REFINE,
    LINE_SPLIT_AFTER_WORD,
    LINE_SPLIT_BY_SELECTION,
    LINE_FORM_PARAGRAPH,
    LINE_GT_TO_OCR,
    LINE_OCR_TO_GT,
    LINE_VALIDATE,
    LINE_UNVALIDATE,
    LINE_DELETE,
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
    page.locator(PARA_EXPANDER).first.wait_for(state="visible", timeout=15_000)


def _wait_for_notification(page: Page, timeout: int = 15_000) -> None:
    """Wait for a Quasar notification to appear."""
    page.locator(".q-notification").first.wait_for(state="visible", timeout=timeout)


def _select_line(page: Page, index: int = 0) -> None:
    """Check the Nth line checkbox (0-based)."""
    checkboxes = page.get_by_label("Select line", exact=True)
    checkboxes.nth(index).wait_for(state="visible", timeout=10_000)
    checkboxes.nth(index).click()
    page.wait_for_timeout(1000)


def _select_word(page: Page, index: int = 0) -> None:
    """Check the Nth word checkbox (0-based)."""
    checkboxes = page.locator(WORD_CHECKBOX)
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
def test_line_scope_buttons_disabled_without_selection(
    browser_app_url: str, browser_page
) -> None:
    """All line-scope buttons are disabled when no line is selected."""
    page = browser_page
    _setup(page, browser_app_url)

    for selector in ALL_LINE_BUTTONS:
        btn = page.locator(selector)
        expect(btn).to_be_visible()
        expect(btn).to_be_disabled()


@pytest.mark.browser
def test_line_scope_buttons_enabled_with_selection(
    browser_app_url: str, browser_page
) -> None:
    """Selecting a line enables most line-scope buttons."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_line(page, 0)

    # Buttons that need 1+ line selected should be enabled
    for selector in [
        LINE_REFINE,
        LINE_EXPAND_REFINE,
        LINE_GT_TO_OCR,
        LINE_OCR_TO_GT,
        LINE_VALIDATE,
        LINE_UNVALIDATE,
        LINE_DELETE,
    ]:
        expect(page.locator(selector)).to_be_enabled()

    # Merge needs 2+ lines — should still be disabled
    expect(page.locator(LINE_MERGE)).to_be_disabled()


@pytest.mark.browser
def test_line_merge_disabled_with_single_selection(
    browser_app_url: str, browser_page
) -> None:
    """Merge is disabled when only 1 line is selected (need 2+)."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_line(page, 0)
    expect(page.locator(LINE_MERGE)).to_be_disabled()


@pytest.mark.browser
def test_line_scope_buttons_have_tooltips(browser_app_url: str, browser_page) -> None:
    """Each line-scope button has a descriptive tooltip on hover."""
    page = browser_page
    _setup(page, browser_app_url)

    buttons_tooltips = [
        (LINE_MERGE, "Merge selected lines"),
        (LINE_REFINE, "Refine selected lines"),
        (LINE_EXPAND_REFINE, "Expand then refine selected lines"),
        (LINE_SPLIT_AFTER_WORD, "Split the selected line"),
        (LINE_SPLIT_BY_SELECTION, "Split line"),
        (LINE_FORM_PARAGRAPH, "Select lines to form a new paragraph"),
        (LINE_GT_TO_OCR, "Copy ground truth text to OCR"),
        (LINE_OCR_TO_GT, "Copy OCR text to ground truth"),
        (LINE_VALIDATE, "Validate all words in selected lines"),
        (LINE_UNVALIDATE, "Unvalidate all words in selected lines"),
        (LINE_DELETE, "Delete selected lines"),
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
def test_line_refine(browser_app_url: str, browser_page) -> None:
    """Select line, click Refine: success notification appears."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_line(page, 0)
    page.locator(LINE_REFINE).click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_line_expand_refine(browser_app_url: str, browser_page) -> None:
    """Select line, click Expand+Refine: success notification appears."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_line(page, 0)
    page.locator(LINE_EXPAND_REFINE).click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_line_copy_gt_to_ocr(browser_app_url: str, browser_page) -> None:
    """Select line, click GT->OCR: OCR labels update to match GT values."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    # Read first GT value before action
    gt_input = _get_gt_inputs(page).first
    expect(gt_input).to_be_visible()
    gt_value = gt_input.input_value()

    _select_line(page, 0)
    page.locator(LINE_GT_TO_OCR).click()
    page.wait_for_timeout(1000)

    # First OCR label should now match the GT value
    ocr_label = _get_ocr_labels(page).first
    expect(ocr_label).to_have_text(gt_value)


@pytest.mark.browser
def test_line_copy_ocr_to_gt(browser_app_url: str, browser_page) -> None:
    """Select line, click OCR->GT: GT inputs update to match OCR labels."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    # Read first OCR label before action
    ocr_label = _get_ocr_labels(page).first
    expect(ocr_label).to_be_visible()
    ocr_value = ocr_label.text_content()

    _select_line(page, 0)
    page.locator(LINE_OCR_TO_GT).click()
    page.wait_for_timeout(1000)

    # First GT input should now equal the OCR value
    gt_input = _get_gt_inputs(page).first
    expect(gt_input).to_have_value(ocr_value)


@pytest.mark.browser
def test_line_validate(browser_app_url: str, browser_page) -> None:
    """Select line, click Validate: word validate buttons turn green."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    page.locator(WORD_VALIDATE_BUTTON).first.wait_for(state="visible", timeout=15_000)

    _select_line(page, 0)
    page.locator(LINE_VALIDATE).click()
    page.wait_for_timeout(1000)

    # First word validate button should be green
    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-green"))


@pytest.mark.browser
def test_line_unvalidate(browser_app_url: str, browser_page) -> None:
    """Validate line first, then Unvalidate: buttons revert to grey."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    page.locator(WORD_VALIDATE_BUTTON).first.wait_for(state="visible", timeout=15_000)

    # Validate first
    _select_line(page, 0)
    page.locator(LINE_VALIDATE).click()
    page.wait_for_timeout(1000)

    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-green"))

    # Now Unvalidate
    page.locator(LINE_UNVALIDATE).click()
    page.wait_for_timeout(1000)

    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-grey"))


@pytest.mark.browser
def test_line_delete(browser_app_url: str, browser_page) -> None:
    """Select line, click Delete: line count decreases by 1."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    # Count line delete buttons (one per line card) before
    lines_before = page.locator(LINE_DELETE_CARD).count()
    assert lines_before > 1, "Need at least 2 lines for delete test"

    _select_line(page, 0)

    delete_btn = page.locator(LINE_DELETE)
    expect(delete_btn).to_be_enabled()
    delete_btn.click()
    page.wait_for_timeout(1000)

    # Line count should decrease by 1
    expect(page.locator(LINE_DELETE_CARD)).to_have_count(lines_before - 1)


@pytest.mark.browser
def test_line_merge_with_selection(browser_app_url: str, browser_page) -> None:
    """Select 2 lines, click Merge: line count decreases by 1."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    # Count lines before
    lines_before = page.locator(LINE_DELETE_CARD).count()
    assert lines_before >= 2, "Need at least 2 lines for merge test"

    # Select two adjacent lines
    _select_line(page, 0)
    _select_line(page, 1)

    merge_btn = page.locator(LINE_MERGE)
    expect(merge_btn).to_be_enabled(timeout=10_000)
    merge_btn.click()
    page.wait_for_timeout(1000)

    # Line count should decrease by 1
    expect(page.locator(LINE_DELETE_CARD)).to_have_count(lines_before - 1)


@pytest.mark.browser
def test_line_form_paragraph(browser_app_url: str, browser_page) -> None:
    """Select line from multi-line paragraph, form new paragraph: count increases."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    paras_before = page.locator(PARA_EXPANDER).count()
    assert paras_before >= 2, "Need at least 2 paragraphs for merge+form test"

    # First merge two paragraphs to create a multi-line paragraph
    para_checkboxes = page.locator('[data-testid="paragraph-checkbox"]')
    para_checkboxes.nth(0).click()
    page.wait_for_timeout(1000)
    para_checkboxes.nth(1).click()
    page.wait_for_timeout(1000)

    merge_btn = page.locator('[data-testid="paragraph-merge-button"]')
    expect(merge_btn).to_be_enabled(timeout=10_000)
    merge_btn.click()
    page.wait_for_timeout(1000)

    paras_after_merge = page.locator(PARA_EXPANDER).count()
    assert paras_after_merge == paras_before - 1

    # Deselect all paragraph checkboxes
    para_checkboxes = page.locator('[data-testid="paragraph-checkbox"]')
    for i in range(para_checkboxes.count()):
        cb = para_checkboxes.nth(i)
        if cb.is_checked():
            cb.click()
            page.wait_for_timeout(300)

    # Now select a line from the merged paragraph and form a new paragraph
    _select_line(page, 0)

    form_para_btn = page.locator(LINE_FORM_PARAGRAPH)
    expect(form_para_btn).to_be_enabled(timeout=10_000)
    form_para_btn.click()
    page.wait_for_timeout(1000)

    _wait_for_notification(page)

    # Paragraph count should increase by 1 (back to original since merge was -1)
    expect(page.locator(PARA_EXPANDER)).to_have_count(paras_before)
