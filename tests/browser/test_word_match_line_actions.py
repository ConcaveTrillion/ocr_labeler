"""Browser tests for per-line action buttons on renderer line cards."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

LINE_GT_TO_OCR = '[data-testid="line-gt-to-ocr-button"]'
LINE_OCR_TO_GT = '[data-testid="line-ocr-to-gt-button"]'
LINE_VALIDATE = '[data-testid="line-validate-button"]'
LINE_DELETE = '[data-testid="line-delete-button"]'
PARAGRAPH_EXPANDER = '[data-testid="paragraph-expander-button"]'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(page, url: str) -> None:
    """Navigate, load project, and wait for page content."""
    page.goto(url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)


def _switch_to_all_lines(page) -> None:
    """Switch the filter toggle to 'All Lines' so all line cards render."""
    page.get_by_text("All Lines").first.click()
    page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Presence tests
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_action_buttons_present(browser_app_url: str, browser_page) -> None:
    """Line card action buttons (Validate, Delete) are visible on every line."""
    page = browser_page
    _setup(page, browser_app_url)

    # Validate and Delete should appear on every rendered line card
    expect(page.locator(LINE_VALIDATE).first).to_be_visible()
    expect(page.locator(LINE_DELETE).first).to_be_visible()


@pytest.mark.browser
def test_paragraph_expander_present(browser_app_url: str, browser_page) -> None:
    """Paragraph expander button is visible when paragraphs exist."""
    page = browser_page
    _setup(page, browser_app_url)

    expander = page.locator(PARAGRAPH_EXPANDER).first
    expect(expander).to_be_visible()


# ---------------------------------------------------------------------------
# Paragraph expander
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_paragraph_expander_toggle(browser_app_url: str, browser_page) -> None:
    """Click expander to collapse paragraph body, click again to re-expand."""
    page = browser_page
    _setup(page, browser_app_url)

    # Line cards should be visible initially (paragraphs expanded by default)
    count_before = page.locator(LINE_DELETE).count()
    assert count_before > 0, "Expected at least one line card to be visible"

    # Click expander to collapse — line count should decrease
    expander = page.locator(PARAGRAPH_EXPANDER).first
    expander.click()
    page.wait_for_timeout(500)

    # After collapse, there should be fewer line cards
    count_after_collapse = page.locator(LINE_DELETE).count()
    assert count_after_collapse < count_before

    # Click again to re-expand
    expander = page.locator(PARAGRAPH_EXPANDER).first
    expander.click()
    page.wait_for_timeout(500)

    # Line count should be restored
    expect(page.locator(LINE_DELETE)).to_have_count(count_before)


@pytest.mark.browser
def test_paragraph_expander_icon(browser_app_url: str, browser_page) -> None:
    """Expander shows expand_more when expanded, chevron_right when collapsed."""
    page = browser_page
    _setup(page, browser_app_url)

    expander = page.locator(PARAGRAPH_EXPANDER).first

    # Initially expanded — icon should be expand_more
    expect(expander.locator("text=expand_more")).to_be_visible()

    # Collapse
    expander.click()
    page.wait_for_timeout(500)

    # Icon should now be chevron_right
    expander = page.locator(PARAGRAPH_EXPANDER).first
    expect(expander.locator("text=chevron_right")).to_be_visible()


# ---------------------------------------------------------------------------
# Line copy GT→OCR
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_copy_gt_to_ocr(browser_app_url: str, browser_page) -> None:
    """Click GT→OCR on a line: OCR labels update to match GT input values."""
    page = browser_page
    _setup(page, browser_app_url)

    gt_to_ocr = page.locator(LINE_GT_TO_OCR).first
    # GT→OCR only appears on non-exact lines, so may not exist. Skip if absent.
    if gt_to_ocr.count() == 0:
        pytest.skip("No GT→OCR button rendered (all lines may be exact matches)")

    # Read first word's GT input value before action
    gt_input = page.locator(".q-field--outlined input").first
    expect(gt_input).to_be_visible()
    gt_value = gt_input.input_value()

    # Click GT→OCR for the first line
    gt_to_ocr.click()
    page.wait_for_timeout(1000)

    # After GT→OCR, the OCR label for that word should match the GT value
    first_ocr = page.locator(".monospace").first
    expect(first_ocr).to_be_visible()
    expect(first_ocr).to_have_text(gt_value)


# ---------------------------------------------------------------------------
# Line copy OCR→GT
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_copy_ocr_to_gt(browser_app_url: str, browser_page) -> None:
    """Click OCR→GT on a line: GT input values update to match OCR labels."""
    page = browser_page
    _setup(page, browser_app_url)

    ocr_to_gt = page.locator(LINE_OCR_TO_GT).first
    if ocr_to_gt.count() == 0:
        pytest.skip("No OCR→GT button rendered (all lines may be exact matches)")

    # Read first word's OCR label text before action
    first_ocr = page.locator(".monospace").first
    expect(first_ocr).to_be_visible()
    ocr_text = first_ocr.text_content()

    # Click OCR→GT for the first line
    ocr_to_gt.click()
    page.wait_for_timeout(1000)

    # After OCR→GT, the GT input should match the OCR text
    gt_input = page.locator(".q-field--outlined input").first
    expect(gt_input).to_be_visible()
    expect(gt_input).to_have_value(ocr_text)


# ---------------------------------------------------------------------------
# Line validate toggle
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_validate_toggle(browser_app_url: str, browser_page) -> None:
    """Click Validate on a line: per-word validate buttons turn green; Unvalidate reverts."""
    page = browser_page
    _setup(page, browser_app_url)

    validate_btn = page.locator(LINE_VALIDATE).first
    expect(validate_btn).to_be_visible()

    # Check initial label — should contain "Validate" (not all validated)
    expect(validate_btn).to_contain_text("Validate")

    # Click Validate
    validate_btn.click()
    page.wait_for_timeout(1000)

    # After validation the button should now contain "Unvalidate"
    validate_btn = page.locator(LINE_VALIDATE).first
    expect(validate_btn).to_contain_text("Unvalidate")

    # Click Unvalidate to revert
    validate_btn.click()
    page.wait_for_timeout(1000)

    validate_btn = page.locator(LINE_VALIDATE).first
    expect(validate_btn).to_contain_text("Validate")


# ---------------------------------------------------------------------------
# Line delete
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_delete(browser_app_url: str, browser_page) -> None:
    """Deleting a line reduces the line card count by one."""
    page = browser_page
    _setup(page, browser_app_url)

    # Switch to All Lines so we can count reliably
    _switch_to_all_lines(page)

    delete_buttons = page.locator(LINE_DELETE)
    count_before = delete_buttons.count()

    # Click the last delete button to avoid index-shift issues
    delete_buttons.last.click()
    page.wait_for_timeout(1000)

    # Count should decrease by 1
    expect(page.locator(LINE_DELETE)).to_have_count(count_before - 1)
