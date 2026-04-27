"""Browser tests for per-line action buttons on renderer line cards."""

from __future__ import annotations

import pytest
from playwright.sync_api import expect

from .helpers import load_project, wait_for_app_ready, wait_for_page_loaded

# ---------------------------------------------------------------------------
# Selectors
# ---------------------------------------------------------------------------

LINE_GT_TO_OCR = '[data-testid="line-gt-to-ocr-button"]'
LINE_OCR_TO_GT = '[data-testid="line-ocr-to-gt-button"]'
LINE_VALIDATE = '[data-testid="line-validate-button"]'
LINE_DELETE = '[data-testid="line-delete-button"]'
LINE_CARD = '[data-testid="line-card"]'
WORD_VALIDATE = '[data-testid="word-validate-button"]'
PARAGRAPH_EXPANDER = '[data-testid="paragraph-expander-button"]'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _setup(page, url: str) -> None:
    """Navigate, load project, and wait for page content."""
    page.goto(url, wait_until="networkidle")
    wait_for_app_ready(page)
    load_project(page, "browser-test-project")
    wait_for_page_loaded(page)


def _switch_to_all_lines(page) -> None:
    """Switch the filter toggle to 'All Lines' so all line cards render."""
    page.get_by_text("All Lines").first.click()
    page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Presence tests
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_action_buttons_present(browser_app_url: str, browser_page) -> None:
    """Line card action buttons (Validate, Delete) are visible on every line."""
    page = browser_page
    _setup(page, browser_app_url)

    # Validate and Delete should appear on every rendered line card
    expect(page.locator(LINE_VALIDATE).first).to_be_visible()
    expect(page.locator(LINE_DELETE).first).to_be_visible()


@pytest.mark.browser
def test_paragraph_expander_present(browser_app_url: str, browser_page) -> None:
    """Paragraph expander button is visible when paragraphs exist."""
    page = browser_page
    _setup(page, browser_app_url)

    expander = page.locator(PARAGRAPH_EXPANDER).first
    expect(expander).to_be_visible()


# ---------------------------------------------------------------------------
# Paragraph expander
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_paragraph_expander_toggle(browser_app_url: str, browser_page) -> None:
    """Click expander to collapse paragraph body, click again to re-expand."""
    page = browser_page
    _setup(page, browser_app_url)

    # Wait for line cards to render, then count
    page.locator(LINE_DELETE).first.wait_for(state="visible", timeout=15_000)
    count_before = page.locator(LINE_DELETE).count()
    assert count_before > 0, "Expected at least one line card to be visible"

    # Click expander to collapse — line count should decrease
    expander = page.locator(PARAGRAPH_EXPANDER).first
    expander.click()
    expect(page.locator(LINE_DELETE)).not_to_have_count(count_before, timeout=5_000)

    # After collapse, there should be fewer line cards
    count_after_collapse = page.locator(LINE_DELETE).count()
    assert count_after_collapse < count_before

    # Click again to re-expand
    expander = page.locator(PARAGRAPH_EXPANDER).first
    expander.click()
    page.wait_for_timeout(500)

    # Line count should be restored
    expect(page.locator(LINE_DELETE)).to_have_count(count_before)


@pytest.mark.browser
def test_paragraph_expander_icon(browser_app_url: str, browser_page) -> None:
    """Expander shows expand_more when expanded, chevron_right when collapsed."""
    page = browser_page
    _setup(page, browser_app_url)

    expander = page.locator(PARAGRAPH_EXPANDER).first

    # Initially expanded — icon should be expand_more
    expect(expander.locator("text=expand_more")).to_be_visible()

    # Collapse
    expander.click()
    page.wait_for_timeout(500)

    # Icon should now be chevron_right
    expander = page.locator(PARAGRAPH_EXPANDER).first
    expect(expander.locator("text=chevron_right")).to_be_visible()


# ---------------------------------------------------------------------------
# Line copy GT→OCR
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_copy_gt_to_ocr(browser_app_url: str, browser_page) -> None:
    """Click GT→OCR on a line: OCR labels update to match GT input values."""
    page = browser_page
    _setup(page, browser_app_url)

    # Wait for line cards to render before checking button presence
    page.locator(LINE_DELETE).first.wait_for(state="visible", timeout=15_000)
    gt_to_ocr = page.locator(LINE_GT_TO_OCR).first
    # GT→OCR only appears on non-exact lines, so may not exist. Skip if absent.
    if gt_to_ocr.count() == 0:
        pytest.skip("No GT→OCR button rendered (all lines may be exact matches)")

    # Read first word's GT input value before action
    gt_input = page.locator(".q-field--outlined input").first
    expect(gt_input).to_be_visible()
    gt_value = gt_input.input_value()

    # Click GT→OCR for the first line
    gt_to_ocr.click()
    page.wait_for_timeout(1000)

    # After GT→OCR, the OCR label for that word should match the GT value
    first_ocr = page.locator(".monospace").first
    expect(first_ocr).to_be_visible()
    expect(first_ocr).to_have_text(gt_value)


# ---------------------------------------------------------------------------
# Line copy OCR→GT
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_copy_ocr_to_gt(browser_app_url: str, browser_page) -> None:
    """Click OCR→GT on a line: GT input values update to match OCR labels."""
    page = browser_page
    _setup(page, browser_app_url)

    # Wait for line cards to render before checking button presence
    page.locator(LINE_DELETE).first.wait_for(state="visible", timeout=15_000)
    ocr_to_gt = page.locator(LINE_OCR_TO_GT).first
    if ocr_to_gt.count() == 0:
        pytest.skip("No OCR→GT button rendered (all lines may be exact matches)")

    # Read first word's OCR label text before action
    first_ocr = page.locator(".monospace").first
    expect(first_ocr).to_be_visible()
    ocr_text = first_ocr.text_content()

    # Click OCR→GT for the first line
    ocr_to_gt.click()
    page.wait_for_timeout(1000)

    # After OCR→GT, the GT input should match the OCR text
    gt_input = page.locator(".q-field--outlined input").first
    expect(gt_input).to_be_visible()
    expect(gt_input).to_have_value(ocr_text)


# ---------------------------------------------------------------------------
# Line validate toggle
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_validate_toggle(browser_app_url: str, browser_page) -> None:
    """Click Validate on a line: per-word validate buttons turn green; Unvalidate reverts."""
    page = browser_page
    _setup(page, browser_app_url)
    _switch_to_all_lines(page)

    validate_btn = page.locator(LINE_VALIDATE).first
    expect(validate_btn).to_be_visible()

    # Check initial label — should contain "Validate" (not all validated)
    expect(validate_btn).to_contain_text("Validate")

    # Click Validate
    validate_btn.click()
    page.wait_for_timeout(1000)

    # After validation the button should now contain "Unvalidate"
    validate_btn = page.locator(LINE_VALIDATE).first
    expect(validate_btn).to_contain_text("Unvalidate")

    # Click Unvalidate to revert
    validate_btn.click()
    page.wait_for_timeout(1000)

    validate_btn = page.locator(LINE_VALIDATE).first
    expect(validate_btn).to_contain_text("Validate")


@pytest.mark.browser
def test_line_validate_validates_all_words(browser_app_url: str, browser_page) -> None:
    """Clicking the per-line Validate button must validate every word in that line.

    Regression: the targeted word-validation event handler in TextTabs was
    comparing against ``self.page_index`` (frozen at construction time) instead
    of the live current page index.  On every page other than the first, the
    handler dropped the event, so the in-memory line match was never updated
    and the rerendered card showed every word as unvalidated even though the
    underlying word labels had been toggled.
    """
    page = browser_page
    _setup(page, browser_app_url)

    # Navigate to page 3 first — the bug only manifested on pages other than
    # the initial page, since TextTabs.page_index defaulted to 0.
    page_input = page.get_by_label("Page")
    page_input.fill("3")
    page_input.press("Enter")
    expect(page_input).to_have_value("3", timeout=15_000)

    _switch_to_all_lines(page)
    page.locator(LINE_VALIDATE).first.wait_for(state="visible", timeout=15_000)

    # Page 1 has 7 lines, page 3 has 35.  Wait until the line card count
    # reflects page 3 — otherwise the navigation may still be pending and we
    # would be operating on page-1 cards while ``current_page_index`` flips
    # to 2 mid-click, causing the targeted validation event to be dropped
    # for the wrong reason.
    expect(page.locator(LINE_CARD)).to_have_count(35, timeout=15_000)

    # Find the first line card with >= 2 OCR words so the bug
    # (only first word validated, or no words validated) is observable.
    cards = page.locator(LINE_CARD)
    target_index = -1
    target_word_count = 0
    for i in range(cards.count()):
        card = cards.nth(i)
        if card.locator(LINE_VALIDATE).count() == 0:
            continue
        wc = card.locator(WORD_VALIDATE).count()
        if wc >= 2:
            target_index = i
            target_word_count = wc
            break

    assert target_index >= 0, "Expected a line card with >= 2 OCR words"

    def target_card():
        # Re-resolve the locator each time: the line card DOM node is
        # replaced by ``rerender_line_card`` on every validation toggle, so
        # any previously captured handle becomes stale.
        return page.locator(LINE_CARD).nth(target_index)

    # All word-validate buttons should start grey (Quasar applies bg-grey for
    # the unvalidated state).
    green_words_before = target_card().locator(f"{WORD_VALIDATE}.bg-green").count()
    assert green_words_before == 0, (
        f"Expected no validated words before click, got {green_words_before}"
    )

    target_card().locator(LINE_VALIDATE).click()
    page.wait_for_timeout(1000)

    # After clicking Validate, every word in the line must be marked validated
    # (Quasar applies bg-green when color=green is set on the button).
    expect(target_card().locator(f"{WORD_VALIDATE}.bg-green")).to_have_count(
        target_word_count
    )

    # And the line-validate button should now read "Unvalidate".
    expect(target_card().locator(LINE_VALIDATE)).to_contain_text("Unvalidate")


# ---------------------------------------------------------------------------
# Line delete
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_line_delete(browser_app_url: str, browser_page) -> None:
    """Deleting a line reduces the line card count by one."""
    page = browser_page
    _setup(page, browser_app_url)

    # Switch to All Lines so we can count reliably
    _switch_to_all_lines(page)

    page.locator(LINE_DELETE).first.wait_for(state="visible", timeout=15_000)
    delete_buttons = page.locator(LINE_DELETE)
    count_before = delete_buttons.count()

    # Click the last delete button to avoid index-shift issues
    delete_buttons.last.click()
    page.wait_for_timeout(1000)

    # Count should decrease by 1
    expect(page.locator(LINE_DELETE)).to_have_count(count_before - 1)


# ---------------------------------------------------------------------------
# Validate removes line from unvalidated filter
# ---------------------------------------------------------------------------


@pytest.mark.browser
def test_validated_line_removed_from_unvalidated_filter(
    browser_app_url: str, browser_page
) -> None:
    """After validating a line in 'Unvalidated Lines' view it should disappear."""
    page = browser_page
    _setup(page, browser_app_url)

    # Default filter is "Unvalidated Lines"
    page.get_by_text("Unvalidated Lines").first.wait_for(
        state="visible", timeout=10_000
    )

    # Count line cards before validation
    page.locator(LINE_VALIDATE).first.wait_for(state="visible", timeout=15_000)
    count_before = page.locator(LINE_VALIDATE).count()
    assert count_before > 0, "Expected at least one unvalidated line"

    # Validate the first line
    page.locator(LINE_VALIDATE).first.click()
    page.wait_for_timeout(1000)

    # The validated line should have been removed from the view
    expect(page.locator(LINE_VALIDATE)).to_have_count(count_before - 1)
