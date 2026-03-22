"""Browser tests for page navigation within a loaded project."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import expect

from .helpers import (
    load_project,
    navigate_to_page,
    wait_for_app_ready,
    wait_for_page_loaded,
)


@pytest.mark.browser
def test_next_button_advances_page(browser_app_url: str, browser_page) -> None:
    """Click Next to advance from page 1 to page 2."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")

    # Click Next
    page.get_by_role("button", name="Next").click()
    wait_for_page_loaded(page)

    # Wait for URL to update to page 2 (most reliable indicator)
    page.wait_for_url("**/page/2", timeout=10_000)


@pytest.mark.browser
def test_prev_button_goes_back(browser_app_url: str, browser_page) -> None:
    """Navigate to page 2, click Prev, verify return to page 1."""
    page = browser_page
    url = browser_app_url.rstrip("/") + "/project/browser-test-project/page/2"
    page.goto(url, wait_until="networkidle")
    page.get_by_role("button", name="Prev").wait_for(state="visible", timeout=60_000)
    wait_for_page_loaded(page)

    page.get_by_role("button", name="Prev").click()
    wait_for_page_loaded(page)

    page.wait_for_url("**/page/1", timeout=10_000)


@pytest.mark.browser
def test_prev_disabled_on_first_page(browser_app_url: str, browser_page) -> None:
    """On page 1, verify the Prev button is disabled."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")

    prev_button = page.get_by_role("button", name="Prev")
    # NiceGUI/Quasar disabled buttons get the 'disabled' CSS class.
    # Use a generous timeout since the binding propagates asynchronously.
    expect(prev_button).to_have_class(re.compile(r"\bdisabled\b"), timeout=10_000)


@pytest.mark.browser
def test_next_disabled_on_last_page(browser_app_url: str, browser_page) -> None:
    """Navigate to the last page (3), verify Next button is disabled."""
    page = browser_page
    url = browser_app_url.rstrip("/") + "/project/browser-test-project/page/3"
    page.goto(url, wait_until="networkidle")
    page.get_by_role("button", name="Next").wait_for(state="visible", timeout=60_000)
    wait_for_page_loaded(page)

    next_button = page.get_by_role("button", name="Next")
    expect(next_button).to_have_class(re.compile(r"\bdisabled\b"), timeout=10_000)


@pytest.mark.browser
def test_goto_navigates_to_page(browser_app_url: str, browser_page) -> None:
    """Enter page number 3 in the input and click Go To."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")

    navigate_to_page(page, 3)

    page.wait_for_url("**/page/3", timeout=10_000)


@pytest.mark.browser
def test_url_updates_on_navigation(browser_app_url: str, browser_page) -> None:
    """After navigating to page 2, verify URL reflects the new page number."""
    page = browser_page
    page.goto(browser_app_url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")

    page.get_by_role("button", name="Next").click()
    wait_for_page_loaded(page)

    page.wait_for_url("**/project/browser-test-project/page/2", timeout=10_000)
