"""Browser tests for page-scope toolbar action buttons."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

PAGE_REFINE = '[data-testid="page-refine-bboxes-button"]'
PAGE_EXPAND_REFINE = '[data-testid="page-expand-refine-bboxes-button"]'
PAGE_GT_TO_OCR = '[data-testid="page-copy-gt-to-ocr-button"]'
PAGE_OCR_TO_GT = '[data-testid="page-copy-ocr-to-gt-button"]'
PAGE_VALIDATE = '[data-testid="page-validate-button"]'
PAGE_UNVALIDATE = '[data-testid="page-unvalidate-button"]'

WORD_VALIDATE_BUTTON = '[data-testid="word-validate-button"]'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(page: Page, url: str) -> None:
    """Navigate, load project, and wait for page content."""
    page.goto(url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)


def _wait_for_notification(page: Page, timeout: int = 15_000) -> None:
    """Wait for a Quasar notification to appear."""
    page.locator(".q-notification").first.wait_for(state="visible", timeout=timeout)


def _get_gt_inputs(page: Page):
    """Return all GT input elements in the word match area."""
    return page.locator(".q-field--outlined input")


def _get_ocr_labels(page: Page):
    """Return OCR label elements (div.monospace, excluding q-field inputs)."""
    return page.locator(".monospace:not(.q-field)")


# ---------------------------------------------------------------------------
# Presence tests
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_page_scope_buttons_present(browser_app_url: str, browser_page) -> None:
    """All 6 page-scope toolbar buttons are visible after project load."""
    page = browser_page
    _setup(page, browser_app_url)

    for selector in [
        PAGE_REFINE,
        PAGE_EXPAND_REFINE,
        PAGE_GT_TO_OCR,
        PAGE_OCR_TO_GT,
        PAGE_VALIDATE,
        PAGE_UNVALIDATE,
    ]:
        expect(page.locator(selector)).to_be_visible()


@pytest.mark.browser
def test_page_scope_buttons_have_tooltips(browser_app_url: str, browser_page) -> None:
    """Each page-scope button has a descriptive tooltip visible on hover."""
    page = browser_page
    _setup(page, browser_app_url)

    buttons_tooltips = [
        (PAGE_REFINE, "Refine all bounding boxes"),
        (PAGE_EXPAND_REFINE, "Expand then refine"),
        (PAGE_GT_TO_OCR, "Copy all ground truth text to OCR"),
        (PAGE_OCR_TO_GT, "Copy all OCR text to ground truth"),
        (PAGE_VALIDATE, "Validate all words"),
        (PAGE_UNVALIDATE, "Unvalidate all words"),
    ]

    for selector, expected_text in buttons_tooltips:
        btn = page.locator(selector)
        btn.hover()
        tooltip = page.get_by_role("tooltip").filter(has_text=expected_text)
        expect(tooltip).to_be_visible()
        # Move away to dismiss tooltip before next hover
        page.mouse.move(0, 0)
        page.wait_for_timeout(300)


# ---------------------------------------------------------------------------
# Click / interaction tests
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_page_refine_bboxes_click(browser_app_url: str, browser_page) -> None:
    """Click Refine: success notification appears."""
    page = browser_page
    _setup(page, browser_app_url)

    page.locator(PAGE_REFINE).click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_page_expand_refine_bboxes_click(browser_app_url: str, browser_page) -> None:
    """Click Expand+Refine: success notification appears."""
    page = browser_page
    _setup(page, browser_app_url)

    page.locator(PAGE_EXPAND_REFINE).click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_page_copy_gt_to_ocr(browser_app_url: str, browser_page) -> None:
    """Click GT→OCR (page): OCR labels update to match GT values."""
    page = browser_page
    _setup(page, browser_app_url)

    # Read first GT input value
    gt_input = _get_gt_inputs(page).first
    expect(gt_input).to_be_visible()
    gt_value = gt_input.input_value()

    # Click page-level GT→OCR
    page.locator(PAGE_GT_TO_OCR).click()
    page.wait_for_timeout(1000)

    # First OCR label should now match the first GT value
    ocr_label = _get_ocr_labels(page).first
    expect(ocr_label).to_have_text(gt_value)


@pytest.mark.browser
def test_page_copy_ocr_to_gt(browser_app_url: str, browser_page) -> None:
    """Click OCR→GT (page): GT inputs update to match OCR label text."""
    page = browser_page
    _setup(page, browser_app_url)

    # Read first OCR label value
    ocr_label = _get_ocr_labels(page).first
    expect(ocr_label).to_be_visible()
    ocr_value = ocr_label.text_content()

    # Click page-level OCR→GT
    page.locator(PAGE_OCR_TO_GT).click()
    page.wait_for_timeout(1000)

    # First GT input should now equal the first OCR value
    gt_input = _get_gt_inputs(page).first
    expect(gt_input).to_have_value(ocr_value)


@pytest.mark.browser
def test_page_validate_all(browser_app_url: str, browser_page) -> None:
    """Click Validate all: all word validate buttons turn green."""
    page = browser_page
    _setup(page, browser_app_url)

    val_buttons = page.locator(WORD_VALIDATE_BUTTON)
    assert val_buttons.count() > 0

    # Click Validate all
    page.locator(PAGE_VALIDATE).click()
    page.wait_for_timeout(1000)

    # All validate buttons should now be green
    val_buttons = page.locator(WORD_VALIDATE_BUTTON)
    for i in range(val_buttons.count()):
        expect(val_buttons.nth(i)).to_have_attribute("class", re.compile(r"bg-green"))


@pytest.mark.browser
def test_page_unvalidate_all(browser_app_url: str, browser_page) -> None:
    """Validate all first, then Unvalidate all: all buttons revert to grey."""
    page = browser_page
    _setup(page, browser_app_url)

    # Validate all first
    page.locator(PAGE_VALIDATE).click()
    page.wait_for_timeout(1000)

    # Confirm all green
    val_buttons = page.locator(WORD_VALIDATE_BUTTON)
    for i in range(val_buttons.count()):
        expect(val_buttons.nth(i)).to_have_attribute("class", re.compile(r"bg-green"))

    # Click Unvalidate all
    page.locator(PAGE_UNVALIDATE).click()
    page.wait_for_timeout(1000)

    # All should revert to grey
    val_buttons = page.locator(WORD_VALIDATE_BUTTON)
    for i in range(val_buttons.count()):
        expect(val_buttons.nth(i)).to_have_attribute("class", re.compile(r"bg-grey"))
