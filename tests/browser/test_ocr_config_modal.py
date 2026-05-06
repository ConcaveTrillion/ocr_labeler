"""Browser tests for the OCR Configuration modal.

The modal's full ``data-testid`` contract was established in
``eb2a41f`` but had zero browser regression coverage. This file adds
the smallest possible smoke tests that exercise the open/close cycle
via testid selectors.

Out of scope (queued for follow-up iterations):
- Rescan Models (requires backend model-scan path).
- Apply with edited values (requires HF / local model availability +
  state mutation). The no-edit Apply lifecycle is covered below.
- Editing the HF revision input or model selects.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from .helpers import wait_for_app_ready

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

OCR_CONFIG_TRIGGER = '[data-testid="ocr-config-trigger-button"]'
OCR_CONFIG_CANCEL = '[data-testid="ocr-config-cancel-button"]'
OCR_CONFIG_APPLY = '[data-testid="ocr-config-apply-button"]'
OCR_RESCAN_MODELS = '[data-testid="ocr-rescan-models-button"]'
OCR_DETECTION_SELECT = '[data-testid="ocr-detection-model-select"]'
OCR_RECOGNITION_SELECT = '[data-testid="ocr-recognition-model-select"]'
OCR_HF_REVISION_INPUT = '[data-testid="ocr-hf-revision-input"]'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(page: Page, url: str) -> None:
    """Navigate to the app and wait for it to be ready (no project load needed)."""
    page.goto(url, wait_until="networkidle")
    wait_for_app_ready(page)


def _open_modal(page: Page) -> None:
    """Open the OCR config modal via the testid'd tune-icon trigger."""
    page.locator(OCR_CONFIG_TRIGGER).click()
    # The Cancel button is a load-bearing visible child rendered only when
    # the dialog is open; assert visibility on it rather than the dialog
    # wrapper (NiceGUI's q-dialog wrapper exists in the DOM regardless).
    expect(page.locator(OCR_CONFIG_CANCEL)).to_be_visible(timeout=10_000)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_ocr_config_trigger_button_present(browser_app_url: str, browser_page) -> None:
    """Tune-icon trigger button visible in header at app start (no project)."""
    page = browser_page
    _setup(page, browser_app_url)

    expect(page.locator(OCR_CONFIG_TRIGGER)).to_be_visible()


@pytest.mark.browser
def test_ocr_config_modal_opens_on_trigger_click(
    browser_app_url: str, browser_page
) -> None:
    """Click trigger -> modal's load-bearing controls become visible."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_modal(page)

    # All three action buttons in the modal footer should now be visible.
    expect(page.locator(OCR_CONFIG_CANCEL)).to_be_visible()
    expect(page.locator(OCR_CONFIG_APPLY)).to_be_visible()
    expect(page.locator(OCR_RESCAN_MODELS)).to_be_visible()
    # And the HF revision input.
    expect(page.locator(OCR_HF_REVISION_INPUT)).to_be_visible()


@pytest.mark.browser
def test_ocr_config_cancel_closes_modal(browser_app_url: str, browser_page) -> None:
    """Open -> Cancel -> modal's load-bearing controls hidden again."""
    page = browser_page
    _setup(page, browser_app_url)
    _open_modal(page)

    page.locator(OCR_CONFIG_CANCEL).click()

    # Apply / Cancel / Rescan are rendered inside the dialog body and should
    # become hidden once the dialog closes (Playwright treats q-dialog
    # backdrop-hidden descendants as not visible).
    expect(page.locator(OCR_CONFIG_CANCEL)).not_to_be_visible(timeout=10_000)
    expect(page.locator(OCR_CONFIG_APPLY)).not_to_be_visible()
    expect(page.locator(OCR_RESCAN_MODELS)).not_to_be_visible()


@pytest.mark.browser
def test_ocr_config_apply_with_no_edits_closes_without_error(
    browser_app_url: str, browser_page
) -> None:
    """Open modal -> click Apply (no edits) -> modal closes, no error notification.

    Apply with no edits is a pure UI lifecycle smoke. The modal's
    ``_apply_selection`` handler:

      * Skips the HF revision setter when ``new_revision == previous_revision``
        (both empty on a fresh app start, so no rescan is triggered).
      * Calls ``command_set_selected_ocr_models`` with the as-opened detection
        and recognition keys, which hit ``set_selected_ocr_models`` in
        ``app_state.py``. That path only validates the keys are in
        ``available_ocr_models`` and updates state — no HF probe, no model
        download, no rescan. With the default ``huggingface`` registration
        always present, the call succeeds and the modal closes.

    On success the handler emits a *positive* "OCR models updated"
    notification, not a negative one. We assert:

      * The modal's footer controls are no longer visible.
      * No ``bg-negative`` Quasar notification appeared (the failure path
        emits ``"Failed to apply OCR models"`` with ``negative`` type).
    """
    page = browser_page
    _setup(page, browser_app_url)
    _open_modal(page)

    page.locator(OCR_CONFIG_APPLY).click()

    # Modal should close — same invariant as the Cancel test.
    expect(page.locator(OCR_CONFIG_CANCEL)).not_to_be_visible(timeout=10_000)
    expect(page.locator(OCR_CONFIG_APPLY)).not_to_be_visible()

    # No negative notification should have been emitted. Quasar renders
    # ``ui.notify(type="negative")`` with a ``bg-negative`` class on the
    # notification node; the success path uses ``bg-positive``.
    assert page.locator(".q-notification.bg-negative").count() == 0


@pytest.mark.browser
def test_ocr_config_hf_revision_edit_reverts_on_cancel(
    browser_app_url: str, browser_page
) -> None:
    """Typing into the HF revision input then pressing Cancel must NOT persist.

    The modal's ``_open`` handler unconditionally resets the input value to
    ``app_state_model.hf_pinned_revision or ""`` (see
    ``ocr_config_modal.py:129-133``), so re-opening after Cancel should
    restore whatever the input held when the modal was first opened. This
    test asserts that contract from the browser side end-to-end.
    """
    page = browser_page
    _setup(page, browser_app_url)
    _open_modal(page)

    # Capture the as-opened value (typically empty on a fresh app start, but
    # we don't hard-code that — whatever's there is the baseline we expect to
    # revert to).
    revision_input = page.locator(OCR_HF_REVISION_INPUT)
    initial_value = revision_input.input_value()

    # Type a value that is unlikely to coincide with the baseline.
    sentinel = "test-revision-cancel-sentinel"
    revision_input.fill(sentinel)
    expect(revision_input).to_have_value(sentinel)

    # Cancel the dialog.
    page.locator(OCR_CONFIG_CANCEL).click()
    expect(page.locator(OCR_CONFIG_CANCEL)).not_to_be_visible(timeout=10_000)

    # Re-open and verify the sentinel did NOT persist.
    _open_modal(page)
    expect(revision_input).to_have_value(initial_value)


@pytest.mark.browser
def test_ocr_config_model_selects_open_menu_and_survive_cancel(
    browser_app_url: str, browser_page
) -> None:
    """Detection/recognition select wrappers open a menu, and modal lifecycle
    preserves their visible state across an open -> cancel -> re-open cycle.

    The modal's ``_open`` handler unconditionally resets each select's value
    to the canonical ``selected_ocr_*_model_key`` on every open (see
    ``ocr_config_modal.py:113-128``). At app start (no trainer outputs
    discovered) the only registered option is ``huggingface``, so we can't
    meaningfully *change* the value from the UI to test revert. Instead we
    assert the weaker but still meaningful invariants:

      * Clicking each testid'd select wrapper opens a Quasar ``q-menu`` with
        at least one selectable option (proves the select is wired up and
        ``_open`` did not crash on it).
      * After cancel + re-open, both wrappers remain visible (proves the
        reset path is idempotent and Cancel doesn't corrupt select state).

    A future iteration with trainer-output fixtures can extend this to a
    full value cancel-revert mirroring the HF revision test above.
    """
    page = browser_page
    _setup(page, browser_app_url)
    _open_modal(page)

    detection_select = page.locator(OCR_DETECTION_SELECT)
    recognition_select = page.locator(OCR_RECOGNITION_SELECT)
    expect(detection_select).to_be_visible()
    expect(recognition_select).to_be_visible()

    # Open the detection select's menu and assert at least one option is
    # listed. Then dismiss the menu by pressing Escape (clicking elsewhere
    # may close the dialog; Escape only closes the inner q-menu in Quasar).
    detection_select.click()
    menu = page.locator(".q-menu").last
    expect(menu).to_be_visible(timeout=5_000)
    assert menu.locator(".q-item").count() >= 1
    page.keyboard.press("Escape")
    expect(menu).not_to_be_visible(timeout=5_000)

    # Same exercise for the recognition select.
    recognition_select.click()
    menu = page.locator(".q-menu").last
    expect(menu).to_be_visible(timeout=5_000)
    assert menu.locator(".q-item").count() >= 1
    page.keyboard.press("Escape")
    expect(menu).not_to_be_visible(timeout=5_000)

    # Cancel the dialog and re-open it; both selects should still be visible
    # — i.e. the open lifecycle is stable across cancels.
    page.locator(OCR_CONFIG_CANCEL).click()
    expect(page.locator(OCR_CONFIG_CANCEL)).not_to_be_visible(timeout=10_000)

    _open_modal(page)
    expect(page.locator(OCR_DETECTION_SELECT)).to_be_visible()
    expect(page.locator(OCR_RECOGNITION_SELECT)).to_be_visible()
