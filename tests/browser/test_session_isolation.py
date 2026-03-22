"""Browser tests for per-session state isolation (multiple tabs)."""

from __future__ import annotations

import pytest

from .helpers import load_project, wait_for_app_ready


@pytest.mark.browser
def test_two_tabs_independent_state(browser_app_url: str, browser_context) -> None:
    """Open two tabs: load project in one, verify the other remains at placeholder."""
    context = browser_context

    # Open two tabs
    tab1 = context.new_page()
    tab2 = context.new_page()

    # Both go to the home page
    tab1.goto(browser_app_url, wait_until="networkidle")
    tab2.goto(browser_app_url, wait_until="networkidle")

    wait_for_app_ready(tab1)
    wait_for_app_ready(tab2)

    # Load project in tab1 only
    load_project(tab1, "browser-test-project")

    # Tab1 should have the project loaded
    tab1.get_by_role("button", name="Next").wait_for(state="visible")

    # Tab2 should still show the placeholder
    tab2.get_by_text("No Project Loaded").first.wait_for(state="visible")

    tab1.close()
    tab2.close()


@pytest.mark.browser
def test_two_tabs_different_pages(browser_app_url: str, browser_context) -> None:
    """Open two tabs at different pages, verify independent page state."""
    context = browser_context

    base_url = browser_app_url.rstrip("/")

    # Tab1 goes to page 1
    tab1 = context.new_page()
    tab1.goto(
        f"{base_url}/project/browser-test-project/page/1", wait_until="networkidle"
    )
    tab1.get_by_role("button", name="Next").wait_for(state="visible", timeout=60_000)

    # Tab2 goes to page 3
    tab2 = context.new_page()
    tab2.goto(
        f"{base_url}/project/browser-test-project/page/3", wait_until="networkidle"
    )
    tab2.get_by_role("button", name="Prev").wait_for(state="visible", timeout=60_000)

    # Verify tab1 is on page 1
    tab1_page_input = tab1.get_by_label("Page")
    assert tab1_page_input.input_value() == "1"

    # Verify tab2 is on page 3
    tab2_page_input = tab2.get_by_label("Page")
    assert tab2_page_input.input_value() == "3"

    tab1.close()
    tab2.close()
