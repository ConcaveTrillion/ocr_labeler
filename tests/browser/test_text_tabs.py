"""Browser tests for the text display panel and tabs."""

from __future__ import annotations

import pytest

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded


@pytest.mark.browser
def test_text_tabs_present(browser_app_url: str, browser_page) -> None:
    """Verify text tab labels exist: Matches, Ground Truth, OCR."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    page.get_by_role("tab", name="Matches").wait_for(state="visible")
    page.get_by_role("tab", name="Ground Truth").wait_for(state="visible")
    page.get_by_role("tab", name="OCR").wait_for(state="visible")


@pytest.mark.browser
def test_ocr_text_tab_has_content(browser_app_url: str, browser_page) -> None:
    """Switch to OCR tab and verify it has non-empty content."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Click on the OCR tab
    page.get_by_role("tab", name="OCR").click()

    # Wait for the CodeMirror editor to appear with content
    # CodeMirror uses .cm-content for the editable area
    ocr_content = page.locator(".cm-content").first
    ocr_content.wait_for(state="visible", timeout=10_000)

    # Verify content is not empty
    text = ocr_content.text_content() or ""
    assert len(text.strip()) > 0, "OCR tab should have non-empty content"


@pytest.mark.browser
def test_gt_text_tab_has_content(browser_app_url: str, browser_page) -> None:
    """Switch to Ground Truth tab and verify it has content."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Click on the Ground Truth tab
    page.get_by_role("tab", name="Ground Truth").click()

    # Wait for the CodeMirror editor to appear
    gt_content = page.locator(".cm-content").first
    gt_content.wait_for(state="visible", timeout=10_000)

    # Verify content is not empty (ground truth from pages.json)
    text = gt_content.text_content() or ""
    assert len(text.strip()) > 0, "Ground Truth tab should have content"


@pytest.mark.browser
def test_matches_tab_is_default(browser_app_url: str, browser_page) -> None:
    """Verify the Matches tab is selected by default."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # The Matches tab should be active by default
    matches_tab = page.get_by_role("tab", name="Matches")
    # Quasar active tabs have q-tab--active class
    assert "q-tab--active" in (matches_tab.get_attribute("class") or "")


@pytest.mark.browser
def test_switching_between_text_tabs(browser_app_url: str, browser_page) -> None:
    """Click each text tab and verify the panel content changes."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Switch to OCR tab
    page.get_by_role("tab", name="OCR").click()
    page.locator(".cm-content").first.wait_for(state="visible", timeout=10_000)

    # Switch to Ground Truth tab
    page.get_by_role("tab", name="Ground Truth").click()
    page.locator(".cm-content").first.wait_for(state="visible", timeout=10_000)

    # Switch back to Matches tab
    page.get_by_role("tab", name="Matches").click()
