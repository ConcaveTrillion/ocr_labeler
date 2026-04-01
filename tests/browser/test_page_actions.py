"""Browser tests for the page action buttons."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_first_gt_input(page):
    """Return the first GT text input in the word match area."""
    return page.locator(".q-field--outlined input").first


def _get_first_ocr_label(page):
    """Return the first OCR label element (monospace label in word columns)."""
    return page.locator(".monospace").first


def _wait_for_notification(page, timeout: int = 15_000):
    """Wait for a Quasar notification to appear."""
    page.locator(".q-notification").first.wait_for(state="visible", timeout=timeout)


# ---------------------------------------------------------------------------
# Presence / label tests
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_action_buttons_present(browser_app_url: str, browser_page) -> None:
    """Verify Reload OCR, Save Page, Load Page buttons exist."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    page.get_by_role("button", name="Reload OCR").wait_for(state="visible")
    page.get_by_role("button", name="Save Page").wait_for(state="visible")
    page.get_by_role("button", name="Load Page").wait_for(state="visible")


@pytest.mark.browser
def test_rematch_gt_button_present(browser_app_url: str, browser_page) -> None:
    """Rematch GT button is visible with tooltip after project load."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    rematch = page.get_by_role("button", name="Rematch GT")
    expect(rematch).to_be_visible()

    # Hover to verify tooltip exists
    rematch.hover()
    expect(page.get_by_text("Re-run ground truth matching")).to_be_visible()


@pytest.mark.browser
def test_rematch_gt_button_not_on_home_page(browser_app_url: str, browser_page) -> None:
    """Rematch GT button is not rendered on the home page (no project loaded)."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)

    rematch = page.get_by_role("button", name="Rematch GT")
    expect(rematch).to_have_count(0)


@pytest.mark.browser
def test_page_name_shows_filename(browser_app_url: str, browser_page) -> None:
    """Verify the current image filename is displayed."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # The page name display should show the image filename (e.g., "001.png")
    page.get_by_text("001.png").first.wait_for(state="visible", timeout=10_000)


# ---------------------------------------------------------------------------
# Click / interaction tests
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_save_page_button_click(browser_app_url: str, browser_page) -> None:
    """Click Save Page and verify a success notification appears."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    page.get_by_role("button", name="Save Page").click()
    _wait_for_notification(page)


@pytest.mark.browser
def test_reload_ocr_button_click(browser_app_url: str, browser_page) -> None:
    """Click Reload OCR: page re-renders and GT input values are preserved."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Read first word's OCR label and GT input before reload
    first_ocr = _get_first_ocr_label(page)
    expect(first_ocr).to_be_visible()
    ocr_text_before = first_ocr.text_content()

    gt_input = _get_first_gt_input(page)
    expect(gt_input).to_be_visible()
    gt_value_before = gt_input.input_value()

    # Click Reload OCR
    page.get_by_role("button", name="Reload OCR").click()
    _wait_for_notification(page)

    # Wait for page to re-render — edit-word-button reappears
    page.locator('[data-testid="edit-word-button"]').first.wait_for(
        state="visible", timeout=15_000
    )

    # OCR label still present with same text
    first_ocr_after = _get_first_ocr_label(page)
    expect(first_ocr_after).to_be_visible()
    expect(first_ocr_after).to_have_text(ocr_text_before)

    # GT input value preserved
    gt_input_after = _get_first_gt_input(page)
    expect(gt_input_after).to_have_value(gt_value_before)


@pytest.mark.browser
def test_load_page_button_click(browser_app_url: str, browser_page) -> None:
    """Click Load Page: GT input values restored from saved JSON."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Read first GT input value before load
    gt_input = _get_first_gt_input(page)
    expect(gt_input).to_be_visible()
    gt_value_before = gt_input.input_value()

    # Click Load Page
    page.get_by_role("button", name="Load Page").click()
    _wait_for_notification(page)

    # Wait for page to re-render
    page.locator('[data-testid="edit-word-button"]').first.wait_for(
        state="visible", timeout=15_000
    )

    # GT input restored (should match saved value, same as before)
    gt_input_after = _get_first_gt_input(page)
    expect(gt_input_after).to_be_visible()
    expect(gt_input_after).to_have_value(gt_value_before)


@pytest.mark.browser
def test_rematch_gt_button_click(browser_app_url: str, browser_page) -> None:
    """Edit GT to 'XYZZY', click Rematch GT: GT reverts to source-matched text."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Edit first word's GT input to a sentinel value
    gt_input = _get_first_gt_input(page)
    expect(gt_input).to_be_visible()
    gt_input.fill("XYZZY")
    gt_input.press("Enter")
    page.wait_for_timeout(500)

    # Click Rematch GT
    page.get_by_role("button", name="Rematch GT").click()
    _wait_for_notification(page)

    # Wait for page to re-render
    page.locator('[data-testid="edit-word-button"]').first.wait_for(
        state="visible", timeout=15_000
    )

    # GT input should no longer contain the sentinel value
    gt_input_after = _get_first_gt_input(page)
    expect(gt_input_after).to_be_visible()
    expect(gt_input_after).not_to_have_value("XYZZY")
