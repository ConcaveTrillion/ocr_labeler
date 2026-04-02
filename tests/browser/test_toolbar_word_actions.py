"""Browser tests for word-scope toolbar action buttons."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

WORD_MERGE = '[data-testid="word-merge-button"]'
WORD_REFINE = '[data-testid="word-refine-bboxes-button"]'
WORD_EXPAND_REFINE = '[data-testid="word-expand-refine-bboxes-button"]'
WORD_FORM_LINE = '[data-testid="word-form-line-button"]'
WORD_FORM_PARAGRAPH = '[data-testid="word-form-paragraph-button"]'
WORD_GT_TO_OCR = '[data-testid="word-copy-gt-to-ocr-button"]'
WORD_OCR_TO_GT = '[data-testid="word-copy-ocr-to-gt-button"]'
WORD_VALIDATE = '[data-testid="word-validate-toolbar-button"]'
WORD_UNVALIDATE = '[data-testid="word-unvalidate-toolbar-button"]'
WORD_DELETE = '[data-testid="word-delete-button"]'

WORD_CHECKBOX = '[data-testid="word-checkbox"]'
WORD_VALIDATE_BUTTON = '[data-testid="word-validate-button"]'
LINE_DELETE_CARD = '[data-testid="line-delete-button"]'
PARA_EXPANDER = '[data-testid="paragraph-expander-button"]'

ALL_WORD_BUTTONS = [
    WORD_MERGE,
    WORD_REFINE,
    WORD_EXPAND_REFINE,
    WORD_FORM_LINE,
    WORD_FORM_PARAGRAPH,
    WORD_GT_TO_OCR,
    WORD_OCR_TO_GT,
    WORD_VALIDATE,
    WORD_UNVALIDATE,
    WORD_DELETE,
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
def test_word_scope_buttons_disabled_without_selection(
    browser_app_url: str, browser_page
) -> None:
    """All word-scope buttons are disabled when no word is selected."""
    page = browser_page
    _setup(page, browser_app_url)

    for selector in ALL_WORD_BUTTONS:
        btn = page.locator(selector)
        expect(btn).to_be_visible()
        expect(btn).to_be_disabled()


@pytest.mark.browser
def test_word_scope_buttons_enabled_with_selection(
    browser_app_url: str, browser_page
) -> None:
    """Selecting a word enables most word-scope buttons."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_word(page, 0)

    # Buttons that need 1+ word selected should be enabled
    for selector in [
        WORD_REFINE,
        WORD_EXPAND_REFINE,
        WORD_GT_TO_OCR,
        WORD_OCR_TO_GT,
        WORD_VALIDATE,
        WORD_UNVALIDATE,
        WORD_DELETE,
    ]:
        expect(page.locator(selector)).to_be_enabled()

    # Merge needs 2+ words — should still be disabled
    expect(page.locator(WORD_MERGE)).to_be_disabled()


@pytest.mark.browser
def test_word_merge_disabled_with_single_selection(
    browser_app_url: str, browser_page
) -> None:
    """Merge is disabled when only 1 word is selected (need 2+)."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_word(page, 0)
    expect(page.locator(WORD_MERGE)).to_be_disabled()


@pytest.mark.browser
def test_word_delete_disabled_without_selection(
    browser_app_url: str, browser_page
) -> None:
    """Delete is disabled when nothing is selected."""
    page = browser_page
    _setup(page, browser_app_url)

    expect(page.locator(WORD_DELETE)).to_be_disabled()


@pytest.mark.browser
def test_word_scope_buttons_have_tooltips(browser_app_url: str, browser_page) -> None:
    """Each word-scope button has a descriptive tooltip on hover."""
    page = browser_page
    _setup(page, browser_app_url)

    # Verify a spread of tooltips (non-adjacent to avoid Quasar animation
    # overlap in headless Chromium where tooltip dismiss is unreliable).
    buttons_tooltips = [
        (WORD_MERGE, "Merge selected words"),
        (WORD_GT_TO_OCR, "Copy ground truth text to OCR"),
        (WORD_DELETE, "Delete selected words"),
    ]

    for selector, expected_text in buttons_tooltips:
        btn = page.locator(selector)
        btn.hover()
        tooltip = page.get_by_role("tooltip").filter(has_text=expected_text)
        expect(tooltip).to_be_visible(timeout=10_000)
        page.mouse.move(0, 0)
        page.wait_for_timeout(800)

    # All word-scope buttons are present
    for selector in [
        WORD_MERGE,
        WORD_REFINE,
        WORD_EXPAND_REFINE,
        WORD_FORM_LINE,
        WORD_FORM_PARAGRAPH,
        WORD_GT_TO_OCR,
        WORD_OCR_TO_GT,
        WORD_VALIDATE,
        WORD_UNVALIDATE,
        WORD_DELETE,
    ]:
        expect(page.locator(selector)).to_be_visible()


# ---------------------------------------------------------------------------
# Click / interaction tests
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_word_refine(browser_app_url: str, browser_page) -> None:
    """Select word, click Refine: success notification appears."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_word(page, 0)
    page.locator(WORD_REFINE).click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_word_expand_refine(browser_app_url: str, browser_page) -> None:
    """Select word, click Expand+Refine: success notification appears."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_word(page, 0)
    page.locator(WORD_EXPAND_REFINE).click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_word_copy_gt_to_ocr(browser_app_url: str, browser_page) -> None:
    """Select word, click GT->OCR: OCR label updates to match GT value."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    # Read first GT value before action
    gt_input = _get_gt_inputs(page).first
    expect(gt_input).to_be_visible()
    gt_value = gt_input.input_value()

    _select_word(page, 0)
    page.locator(WORD_GT_TO_OCR).click()
    page.wait_for_timeout(1000)

    # First OCR label should now match the GT value
    ocr_label = _get_ocr_labels(page).first
    expect(ocr_label).to_have_text(gt_value)


@pytest.mark.browser
def test_word_copy_ocr_to_gt(browser_app_url: str, browser_page) -> None:
    """Select word, click OCR->GT: GT input updates to match OCR label."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    # Read first OCR label before action
    ocr_label = _get_ocr_labels(page).first
    expect(ocr_label).to_be_visible()
    ocr_value = ocr_label.text_content()

    _select_word(page, 0)
    page.locator(WORD_OCR_TO_GT).click()
    page.wait_for_timeout(1000)

    # First GT input should now equal the OCR value
    gt_input = _get_gt_inputs(page).first
    expect(gt_input).to_have_value(ocr_value)


@pytest.mark.browser
def test_word_validate(browser_app_url: str, browser_page) -> None:
    """Select word, click Validate: word validate button turns green."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    page.locator(WORD_VALIDATE_BUTTON).first.wait_for(state="visible", timeout=15_000)

    _select_word(page, 0)
    page.locator(WORD_VALIDATE).click()
    page.wait_for_timeout(1000)

    # First word validate button should be green
    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-green"))


@pytest.mark.browser
def test_word_unvalidate(browser_app_url: str, browser_page) -> None:
    """Validate word first, then Unvalidate: button reverts to grey."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    page.locator(WORD_VALIDATE_BUTTON).first.wait_for(state="visible", timeout=15_000)

    # Validate first
    _select_word(page, 0)
    page.locator(WORD_VALIDATE).click()
    page.wait_for_timeout(1000)

    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-green"))

    # Now Unvalidate
    page.locator(WORD_UNVALIDATE).click()
    page.wait_for_timeout(1000)

    val_btn = page.locator(WORD_VALIDATE_BUTTON).first
    expect(val_btn).to_have_attribute("class", re.compile(r"bg-grey"))


@pytest.mark.browser
def test_word_delete(browser_app_url: str, browser_page) -> None:
    """Select word, click Delete: notification confirms deletion."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    _select_word(page, 0)

    delete_btn = page.locator(WORD_DELETE)
    expect(delete_btn).to_be_enabled()
    delete_btn.click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_word_merge_with_selection(browser_app_url: str, browser_page) -> None:
    """Select 2 adjacent words on same line, click Merge: word count decreases."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    words_before = page.locator(WORD_CHECKBOX).count()
    assert words_before >= 2, "Need at least 2 words for merge test"

    # Try selecting pairs of adjacent words until we find two on the same line
    merge_btn = page.locator(WORD_MERGE)
    found_pair = False
    # Only try first few pairs to avoid timeout
    for i in range(min(words_before - 1, 5)):
        _select_word(page, i)
        _select_word(page, i + 1)
        page.wait_for_timeout(1500)  # Wait for button state to update
        if not merge_btn.is_disabled():
            found_pair = True
            break
        # Deselect both
        _select_word(page, i)  # toggle off
        _select_word(page, i + 1)  # toggle off
        page.wait_for_timeout(500)

    if not found_pair:
        pytest.skip("No adjacent words on same line found in fixture data")

    merge_btn.click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_word_form_line(browser_app_url: str, browser_page) -> None:
    """Select words, form new line: line count increases by 1."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    lines_before = page.locator(LINE_DELETE_CARD).count()

    _select_word(page, 0)

    form_line_btn = page.locator(WORD_FORM_LINE)
    expect(form_line_btn).to_be_enabled(timeout=10_000)
    form_line_btn.click()
    page.wait_for_timeout(1000)

    _wait_for_notification(page)

    # Line count should increase by 1
    expect(page.locator(LINE_DELETE_CARD)).to_have_count(lines_before + 1)


@pytest.mark.browser
def test_word_form_paragraph(browser_app_url: str, browser_page) -> None:
    """Select words, form new paragraph: paragraph count increases by 1."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    paras_before = page.locator(PARA_EXPANDER).count()

    _select_word(page, 0)

    form_para_btn = page.locator(WORD_FORM_PARAGRAPH)
    expect(form_para_btn).to_be_enabled(timeout=10_000)
    form_para_btn.click()
    page.wait_for_timeout(1000)

    _wait_for_notification(page)

    # Paragraph count should increase by 1
    expect(page.locator(PARA_EXPANDER)).to_have_count(paras_before + 1)
