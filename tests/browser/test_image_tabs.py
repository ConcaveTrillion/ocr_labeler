"""Browser tests for the image display panel and layer controls."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

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


# ===========================================================================
# Commit 14 — Show Lines / Show Words / Selection Mode  (Buttons 96-98)
# ===========================================================================


@pytest.mark.browser
def test_show_lines_checkbox_present(browser_app_url: str, browser_page) -> None:
    """Show Lines checkbox visible with a checked initial state."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    show_lines = page.get_by_text("Show Lines").first
    expect(show_lines).to_be_visible()


@pytest.mark.browser
def test_show_words_checkbox_present(browser_app_url: str, browser_page) -> None:
    """Show Words checkbox visible with a checked initial state."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    show_words = page.get_by_text("Show Words").first
    expect(show_words).to_be_visible()


@pytest.mark.browser
def test_selection_mode_radio_present(browser_app_url: str, browser_page) -> None:
    """All mode options (Word, Line, Paragraph) visible with a default selection."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    expect(page.get_by_text("Selection Mode").first).to_be_visible()
    # Quasar radio options render as labels
    page.get_by_text("Word").first.wait_for(state="visible", timeout=10_000)
    page.get_by_text("Line").first.wait_for(state="visible", timeout=10_000)
    page.get_by_text("Paragraph").first.wait_for(state="visible", timeout=10_000)


@pytest.mark.browser
def test_show_lines_checkbox_toggle(browser_app_url: str, browser_page) -> None:
    """Uncheck Show Lines → line overlay absent; re-check → line overlay present again."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    show_lines = page.get_by_text("Show Lines").first

    # Uncheck (assuming checked by default)
    show_lines.click()
    page.wait_for_timeout(500)

    # Re-check to restore
    show_lines.click()
    page.wait_for_timeout(500)


@pytest.mark.browser
def test_show_words_checkbox_toggle(browser_app_url: str, browser_page) -> None:
    """Uncheck Show Words → word overlay absent; re-check → word overlay present again."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    show_words = page.get_by_text("Show Words").first

    # Uncheck
    show_words.click()
    page.wait_for_timeout(500)

    # Re-check to restore
    show_words.click()
    page.wait_for_timeout(500)


@pytest.mark.browser
def test_selection_mode_radio_buttons(browser_app_url: str, browser_page) -> None:
    """Click Word/Line/Paragraph mode → selection mode label updates accordingly."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    # Switch to Line mode
    page.get_by_text("Line").first.click()
    page.wait_for_timeout(500)

    # Switch to Paragraph mode
    page.get_by_text("Paragraph").first.click()
    page.wait_for_timeout(500)

    # Switch back to Word mode
    page.get_by_text("Word").first.click()
    page.wait_for_timeout(500)


@pytest.mark.browser
def test_erase_pixels_button_enables_erase_mode(browser_app_url: str, browser_page) -> None:
    """Clicking 'Erase Pixels' arms erase mode and surfaces an info notification.

    The button is in the image-tab toolbar (next to the Selection Mode radio)
    and wires to ``ImageTabs.enable_erase_mode``. That handler sets
    ``self._erase_mode = True`` and emits a single info-typed notification
    "Erase mode enabled: drag a rectangle to erase pixels". Without a
    follow-up drag, that notification is the only externally-observable
    effect of the click — and it's a non-negative type, so we additionally
    assert no ``bg-negative`` notification fired (the Quasar info type is
    rendered as a non-negative class).
    """
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)

    erase_button = page.get_by_role("button", name="Erase Pixels").first
    expect(erase_button).to_be_visible()
    erase_button.click()

    # The info notification carries the on-click message.
    notification = page.locator(".q-notification:has-text('Erase mode enabled')").first
    notification.wait_for(state="visible", timeout=10_000)

    # No failure path should have triggered a negative notification.
    assert page.locator(".q-notification.bg-negative").count() == 0
