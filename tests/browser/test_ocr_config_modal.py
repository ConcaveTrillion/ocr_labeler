"""Browser tests for the OCR Configuration modal.

The modal's full ``data-testid`` contract was established in
``eb2a41f`` but had zero browser regression coverage. This file adds
the smallest possible smoke tests that exercise the open/close cycle
via testid selectors.

Out of scope (queued for follow-up iterations):
- Rescan Models (requires backend model-scan path).
- Apply (requires HF / local model availability + state mutation).
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
