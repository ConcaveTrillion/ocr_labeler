"""Browser tests for the image display panel and layer controls."""

from __future__ import annotations

import pytest

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded


@pytest.mark.browser
def test_layer_controls_present(browser_app_url: str, browser_page) -> None:
    """Verify layer checkbox controls exist after loading a project."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    page.get_by_text("Layers").first.wait_for(state="visible")
    # NiceGUI/Quasar checkboxes render as q-checkbox with text labels
    page.get_by_text("Show Paragraphs").first.wait_for(state="visible")
    page.get_by_text("Show Lines").first.wait_for(state="visible")
    page.get_by_text("Show Words").first.wait_for(state="visible")


@pytest.mark.browser
def test_viewport_image_shows(browser_app_url: str, browser_page) -> None:
    """On load, verify the viewport image element is visible."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # The interactive image viewport should be present
    viewport = page.locator(".ocr-viewport-img").first
    viewport.wait_for(state="visible", timeout=30_000)


@pytest.mark.browser
def test_selection_mode_controls(browser_app_url: str, browser_page) -> None:
    """Verify selection mode radio buttons exist."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    page.get_by_text("Selection Mode").first.wait_for(state="visible")


@pytest.mark.browser
def test_toggling_layer_checkboxes(browser_app_url: str, browser_page) -> None:
    """Toggle layer checkboxes and verify they respond."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Toggle Show Paragraphs checkbox (use text locator for Quasar checkboxes)
    paragraphs_cb = page.get_by_text("Show Paragraphs").first
    paragraphs_cb.click()
    # Click again to restore
    paragraphs_cb.click()
