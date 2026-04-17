"""Browser tests for keyboard shortcuts and GT text editing (Commit 13)."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from .helpers import (
    load_project,
    wait_for_app_ready,
    wait_for_page_loaded,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(page: Page, url: str) -> None:
    """Navigate, load project, and wait for page content."""
    page.goto(url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)


# ---------------------------------------------------------------------------
# Standard: page input present
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_page_input_present(browser_app_url: str, browser_page) -> None:
    """Page number input visible with correct initial value after project load."""
    page = browser_page
    _setup(page, browser_app_url)

    page_input = page.get_by_label("Page")
    expect(page_input).to_be_visible()
    # Initial value should be 1
    expect(page_input).to_have_value("1")


@pytest.mark.browser
def test_page_input_accepts_only_valid_numbers(
    browser_app_url: str, browser_page
) -> None:
    """Entering a non-numeric value does not navigate away from current page."""
    page = browser_page
    _setup(page, browser_app_url)

    page_input = page.get_by_label("Page")
    # Fill with 0 (below minimum of 1) and press Enter
    page_input.fill("0")
    page_input.press("Enter")
    page.wait_for_timeout(1500)

    # URL should not have changed to page/0
    assert "page/0" not in page.url


# ---------------------------------------------------------------------------
# Button 13: Enter in page input navigates
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_enter_in_page_input_navigates(browser_app_url: str, browser_page) -> None:
    """Fill page input with '2' → press Enter → URL contains 'page/2'."""
    page = browser_page
    _setup(page, browser_app_url)

    page_input = page.get_by_label("Page")
    page_input.fill("2")
    page.wait_for_timeout(200)
    page_input.press("Enter")

    page.wait_for_url(re.compile(r"page/2"), timeout=15_000)
    wait_for_page_loaded(page)

    # Verify page content has changed (page input now shows 2)
    expect(page.get_by_label("Page")).to_have_value("2")


# ---------------------------------------------------------------------------
# Button 93: Enter in GT input commits
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_enter_in_gt_input_commits(browser_app_url: str, browser_page) -> None:
    """Open word edit dialog → type in GT input → press Enter → value persists."""
    page = browser_page
    _setup(page, browser_app_url)

    # Open word edit dialog
    edit_btn = page.locator('[data-testid="edit-word-button"]').first
    edit_btn.click()
    page.get_by_text("Merge / Split").first.wait_for(state="visible", timeout=10_000)

    dialog = page.locator(".q-dialog").last
    gt_input = dialog.get_by_label("GT")
    expect(gt_input).to_be_visible()

    gt_input.fill("XYZZY_KSC")
    page.wait_for_timeout(200)
    gt_input.press("Enter")
    page.wait_for_timeout(500)

    # Value should still be set
    expect(gt_input).to_have_value("XYZZY_KSC")

    # Clean up: close dialog without saving
    page.locator('[data-testid="dialog-close-button"]').click()
    page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Button 108: GT text input inline edit
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_gt_text_input_edit(browser_app_url: str, browser_page) -> None:
    """Click inline GT input → clear and type 'XYZZY' → click away → value persists."""
    page = browser_page
    _setup(page, browser_app_url)

    # Wait for GT inputs to render (page 1 has OCR data with GT text inputs)
    gt_inputs = page.locator('[data-testid="gt-text-input"]')
    gt_inputs.first.wait_for(state="visible", timeout=10_000)

    first_input = gt_inputs.first
    first_input.click()
    first_input.fill("XYZZY_INLINE")
    page.wait_for_timeout(300)

    # Click away to blur
    page.locator("body").click()
    page.wait_for_timeout(500)

    # Value should persist after blur
    assert first_input.input_value() == "XYZZY_INLINE"
