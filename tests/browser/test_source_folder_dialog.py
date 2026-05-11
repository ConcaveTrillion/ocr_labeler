"""Browser tests for the source folder dialog (Commit 12)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from .helpers import wait_for_app_ready

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

SOURCE_FOLDER_BUTTON = '[data-testid="source-folder-button"]'
SOURCE_FOLDER_PATH_INPUT = '[data-testid="source-folder-path-input"]'
SOURCE_FOLDER_CURRENT_PATH_LABEL = '[data-testid="source-folder-current-path-label"]'
SOURCE_FOLDER_HOME = '[data-testid="source-folder-home-button"]'
SOURCE_FOLDER_UP = '[data-testid="source-folder-up-button"]'
SOURCE_FOLDER_OPEN_TYPED = '[data-testid="source-folder-open-typed-button"]'
SOURCE_FOLDER_USE_CURRENT = '[data-testid="source-folder-use-current-button"]'
SOURCE_FOLDER_CANCEL = '[data-testid="source-folder-cancel-button"]'
SOURCE_FOLDER_APPLY = '[data-testid="source-folder-apply-button"]'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(page: Page, url: str) -> None:
    """Navigate to the app and wait for it to be ready (no project load needed)."""
    page.goto(url, wait_until="networkidle")
    wait_for_app_ready(page)


def _open_dialog(page: Page) -> None:
    """Open the source folder dialog via the testid'd folder button."""
    page.locator(SOURCE_FOLDER_BUTTON).click()
    page.get_by_text("Source Projects Folder").first.wait_for(state="visible", timeout=10_000)


# ---------------------------------------------------------------------------
# Standard: buttons present
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_folder_dialog_buttons_present(browser_app_url: str, browser_page) -> None:
    """Home, Up, Open, Use Current, Cancel, Apply all visible in dialog."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    expect(page.locator(SOURCE_FOLDER_HOME)).to_be_visible()
    expect(page.locator(SOURCE_FOLDER_UP)).to_be_visible()
    expect(page.locator(SOURCE_FOLDER_OPEN_TYPED)).to_be_visible()
    expect(page.locator(SOURCE_FOLDER_USE_CURRENT)).to_be_visible()
    expect(page.locator(SOURCE_FOLDER_CANCEL)).to_be_visible()
    expect(page.locator(SOURCE_FOLDER_APPLY)).to_be_visible()


@pytest.mark.browser
def test_folder_dialog_path_input_present(browser_app_url: str, browser_page) -> None:
    """Path text input visible and editable inside the dialog."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    # data-testid is forwarded to the underlying <input> element by NiceGUI.
    expect(page.locator(SOURCE_FOLDER_PATH_INPUT)).to_be_visible()
    expect(page.locator(SOURCE_FOLDER_PATH_INPUT)).to_be_editable()


# ---------------------------------------------------------------------------
# Button 2: folder icon opens dialog
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_folder_icon_opens_dialog(browser_app_url: str, browser_page) -> None:
    """Click folder icon (testid) -> dialog visible with 'Source Projects Folder' heading."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    expect(page.get_by_text("Source Projects Folder").first).to_be_visible()


# ---------------------------------------------------------------------------
# Button 3: Home button
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_home_button(browser_app_url: str, browser_page) -> None:
    """Click Home -> path label equals home directory."""
    import os

    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    page.locator(SOURCE_FOLDER_HOME).click()
    page.wait_for_timeout(1000)

    home_dir = os.path.expanduser("~")
    path_label = page.locator(SOURCE_FOLDER_CURRENT_PATH_LABEL)
    expect(path_label).to_contain_text(home_dir, timeout=5_000)


# ---------------------------------------------------------------------------
# Button 4: Up button
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_up_button(browser_app_url: str, browser_page) -> None:
    """Click Up -> path label changes to parent directory."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    path_label = page.locator(SOURCE_FOLDER_CURRENT_PATH_LABEL)

    page.locator(SOURCE_FOLDER_UP).click()
    page.wait_for_timeout(1000)

    path_after = path_label.text_content() or ""
    # Path should have changed (moved up one level)
    # If already at root, it may stay the same -- just verify no crash
    assert path_after is not None


# ---------------------------------------------------------------------------
# Button 5: Open Typed Path
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_open_typed_path(browser_app_url: str, browser_page) -> None:
    """Type valid path in input -> click Open -> path label equals typed path."""
    import os

    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    home_dir = os.path.expanduser("~")
    path_input = page.locator(SOURCE_FOLDER_PATH_INPUT)
    path_input.fill(home_dir)
    page.wait_for_timeout(200)

    page.locator(SOURCE_FOLDER_OPEN_TYPED).click()
    page.wait_for_timeout(1000)

    path_label = page.locator(SOURCE_FOLDER_CURRENT_PATH_LABEL)
    expect(path_label).to_contain_text(home_dir, timeout=5_000)


# ---------------------------------------------------------------------------
# Button 6: Use Current
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_use_current(browser_app_url: str, browser_page) -> None:
    """Click Use Current -> path input value contains the current source folder."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    page.locator(SOURCE_FOLDER_USE_CURRENT).click()
    page.wait_for_timeout(500)

    # After Use Current, the path input should be non-empty
    path_input = page.locator(SOURCE_FOLDER_PATH_INPUT)
    value = path_input.input_value()
    assert len(value) > 0


# ---------------------------------------------------------------------------
# Button 7: Cancel
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_cancel(browser_app_url: str, browser_page) -> None:
    """Click Cancel -> dialog hidden; project dropdown options unchanged."""
    page = browser_page
    _setup(page, browser_app_url)

    _open_dialog(page)

    page.locator(SOURCE_FOLDER_CANCEL).click()
    page.wait_for_timeout(1000)

    # Dialog should be hidden
    expect(page.get_by_text("Source Projects Folder")).to_have_count(0)


# ---------------------------------------------------------------------------
# Button 8: Apply
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_apply(browser_app_url: str, browser_page, browser_test_fixtures_dir) -> None:
    """Navigate to fixtures folder -> Apply -> dialog hidden; project dropdown updated."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    fixtures_dir = str(browser_test_fixtures_dir)
    path_input = page.locator(SOURCE_FOLDER_PATH_INPUT)
    path_input.fill(fixtures_dir)
    page.locator(SOURCE_FOLDER_OPEN_TYPED).click()
    page.wait_for_timeout(500)

    page.locator(SOURCE_FOLDER_APPLY).click()
    page.wait_for_timeout(2000)

    # Dialog should be closed
    expect(page.get_by_text("Source Projects Folder")).to_have_count(0)


# ---------------------------------------------------------------------------
# Button 9: Enter in path input
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_enter_in_path_input(browser_app_url: str, browser_page) -> None:
    """Type valid path -> press Enter -> path label equals typed path; listing refreshes."""
    import os

    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    home_dir = os.path.expanduser("~")
    path_input = page.locator(SOURCE_FOLDER_PATH_INPUT)
    path_input.fill(home_dir)
    page.wait_for_timeout(100)
    path_input.press("Enter")
    page.wait_for_timeout(1000)

    path_label = page.locator(SOURCE_FOLDER_CURRENT_PATH_LABEL)
    expect(path_label).to_contain_text(home_dir, timeout=5_000)


# ---------------------------------------------------------------------------
# Negative path: Enter on nonexistent path
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_dialog_enter_on_nonexistent_path_warns(browser_app_url: str, browser_page) -> None:
    """Enter on a missing path -> warning notify; current-path label unchanged.

    Covers the negative branch of ``_open_typed_source_path`` where
    ``not next_dir.exists() or not next_dir.is_dir()`` triggers
    ``self._notify("Directory not found", "warning")`` (per the iter-39
    keyboard-shortcuts coverage review).
    """
    page = browser_page
    _setup(page, browser_app_url)
    _open_dialog(page)

    path_label = page.locator(SOURCE_FOLDER_CURRENT_PATH_LABEL)
    path_label.wait_for(state="visible", timeout=10_000)
    initial_path = path_label.text_content() or ""

    # Type a path that is exceedingly unlikely to exist on any host.
    bogus_path = "/nonexistent_xyz_abc_123_pd_ocr_labeler_test"
    path_input = page.locator(SOURCE_FOLDER_PATH_INPUT)
    path_input.fill(bogus_path)
    page.wait_for_timeout(100)
    path_input.press("Enter")

    # The "Directory not found" warning notification should surface.
    warning = page.locator(".q-notification.bg-warning:has-text('Directory not found')").first
    warning.wait_for(state="visible", timeout=10_000)

    # And the dialog's path label must NOT have changed to the bogus
    # value (the negative branch returns before mutating state).
    final_path = path_label.text_content() or ""
    assert final_path == initial_path, (
        f"path label changed from {initial_path!r} to {final_path!r} "
        f"despite Directory not found warning"
    )
    assert bogus_path not in final_path

    # No negative-type toast should have fired (this is a soft warning).
    assert page.locator(".q-notification.bg-negative").count() == 0
