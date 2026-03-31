# Browser UI Test Plan

Phased plan for achieving full browser-test coverage of every action button
listed in `docs/architecture/ui-action-buttons.md`.

## Conventions

All new tests follow the existing patterns in `tests/browser/`:

- Mark every test `@pytest.mark.browser`.
- Fixtures: `browser_app_url`, `browser_page` (single tab),
  `browser_context` (multi-tab).
- Use helpers from `tests/browser/helpers.py`
  (`load_project`, `wait_for_page_loaded`, `navigate_to_page`, …).
- Selectors: prefer `data-testid`, then `get_by_role`, then `get_by_text`,
  then CSS class as last resort.
- New `data-testid` attributes will be added to source components as
  needed — each commit that adds tests may also add minimal `data-testid`
  props.
- Each commit is self-contained: tests pass independently.

---

## Commit 1 — Page Actions: interaction tests for untested buttons

**File:** `tests/browser/test_page_actions.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 14 | `test_reload_ocr_button_click` | Click Reload OCR → word match list re-renders, success notification "Page reloaded" appears |
| 16 | `test_load_page_button_click` | Click Load Page → word match content refreshes with loaded state, success notification "Page loaded" appears |
| 17 | `test_rematch_gt_button_present` | Rematch GT button visible with tooltip after project load |
| 17 | `test_rematch_gt_button_click` | Click Rematch GT → GT text fields update, match status colours refresh, success notification appears |

**Estimated size:** ~50 lines of new test code.

---

## Commit 2 — Per-line action buttons (renderer line cards)

**File:** `tests/browser/test_word_match_line_actions.py` (new)

Requires: `data-testid` attributes on line-card action buttons in
`word_match_renderer.py` (or tooltip-based selectors).

| Button # | Test | What it verifies |
| --- | --- | --- |
| 57 | `test_paragraph_expander_toggle` | Click expander → paragraph body collapses (hidden); click again → body re-appears |
| 58 | `test_line_copy_gt_to_ocr` | Click GT→OCR → OCR text fields in that line update to match GT values |
| 59 | `test_line_copy_ocr_to_gt` | Click OCR→GT → GT text fields in that line update to match OCR values |
| 60 | `test_line_validate_toggle` | Click Validate → word icons turn green; line header shows validated count; click Unvalidate → icons revert to grey |
| 61 | `test_line_delete` | Click delete → line card element removed from DOM, total line count decreases |

**Source changes:** Add `data-testid` to line-card action buttons in
`word_match_renderer.py`.

**Estimated size:** ~80 lines of test code, ~10 lines of source changes.

---

## Commit 3 — Per-word buttons (validate toggle, tag clear)

**File:** `tests/browser/test_word_match.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 63 | `test_word_validate_toggle` | Click validate icon → icon colour changes grey→green; click again → reverts green→grey; stats label updates |
| 64 | `test_word_tag_clear_in_renderer` | Hover tag chip → clear button appears; click clear → chip element removed from DOM |
| 107 | `test_line_checkbox_selection` | Check line checkbox → line-scope toolbar buttons become enabled; uncheck → buttons disable |

**Source changes:** May need `data-testid` on word validate button if
tooltip selectors are unreliable.

**Estimated size:** ~60 lines.

---

## Commit 4 — Toolbar: page-scope actions

**File:** `tests/browser/test_toolbar_page_actions.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 18 | `test_page_refine_bboxes_click` | Click Refine → success notification "Bounding boxes refined"; word images refresh (src attributes change) |
| 19 | `test_page_expand_refine_bboxes_click` | Click Expand+Refine → success notification "expanded and refined"; word images refresh |
| 20 | `test_page_copy_gt_to_ocr` | Click GT→OCR (page) → all OCR text fields update to match GT text; success notification with line count |
| 21 | `test_page_copy_ocr_to_gt` | Click OCR→GT (page) → all GT text fields update to match OCR text; success notification with line count |
| 22 | `test_page_validate_all` | Click Validate all → all word validate icons turn green; stats label shows all validated |
| 23 | `test_page_unvalidate_all` | Validate all first, then Unvalidate all → all icons revert to grey; stats label shows 0 validated |

**Source changes:** Add `data-testid` to page-row toolbar buttons in
`word_match_toolbar.py`.

**Estimated size:** ~90 lines of test code, ~15 lines of source changes.

---

## Commit 5 — Toolbar: paragraph-scope actions

**File:** `tests/browser/test_toolbar_paragraph_actions.py` (new)

Prerequisite: select a paragraph (expand paragraph → check line checkboxes
or word checkboxes within it).

| Button # | Test | What it verifies |
| --- | --- | --- |
| 24 | `test_paragraph_merge` | Select 2 paragraphs → merge → paragraph count decreases by 1; lines consolidated into first |
| 25 | `test_paragraph_refine` | Select paragraph → click Refine → success notification; word images refresh |
| 26 | `test_paragraph_expand_refine` | Select paragraph → click Expand+Refine → success notification; word images refresh |
| 27 | `test_paragraph_split_after_line` | Select a line within paragraph → split → paragraph count increases by 1 |
| 28 | `test_paragraph_copy_gt_to_ocr` | Select paragraph → click GT→OCR → OCR text fields in paragraph update to match GT; selection cleared |
| 29 | `test_paragraph_copy_ocr_to_gt` | Select paragraph → click OCR→GT → GT text fields in paragraph update to match OCR; selection cleared |
| 30 | `test_paragraph_validate` | Select paragraph → Validate → all word icons in paragraph turn green; line headers show full validation |
| 31 | `test_paragraph_unvalidate` | Validate first, then Unvalidate → icons revert to grey; line headers show 0 validated |
| 32 | `test_paragraph_delete` | Select paragraph → Delete → paragraph container removed from DOM; total paragraph count decreases |

**Source changes:** Add `data-testid` to paragraph-row toolbar buttons.

**Estimated size:** ~120 lines of test code, ~20 lines of source changes.

---

## Commit 6 — Toolbar: line-scope actions

**File:** `tests/browser/test_toolbar_line_actions.py` (new)

Prerequisite: select lines via line checkboxes.

| Button # | Test | What it verifies |
| --- | --- | --- |
| 33 | `test_line_merge_with_selection` | Select 2 lines → merge → line count decreases by 1; words consolidated into first line |
| 34 | `test_line_refine` | Select line → click Refine → success notification; word images in line refresh |
| 35 | `test_line_expand_refine` | Select line → click Expand+Refine → success notification; word images refresh |
| 36 | `test_line_split_after_word` | Select word in middle of line → split → line count increases by 1; words distributed |
| 37 | `test_line_split_by_selection` | Select subset of words → split by selection → line count increases; selected words in new line |
| 38 | `test_line_form_paragraph` | Select lines → form new paragraph → paragraph count increases by 1; lines moved |
| 39 | `test_line_copy_gt_to_ocr` | Select line → GT→OCR → OCR text fields in selected lines update to match GT; selection cleared |
| 40 | `test_line_copy_ocr_to_gt` | Select line → OCR→GT → GT text fields in selected lines update to match OCR; selection cleared |
| 41 | `test_line_validate` | Select line → Validate → all word icons in line turn green; line header shows full validation |
| 42 | `test_line_unvalidate` | Validate first, then Unvalidate → icons revert to grey; line header shows 0 validated |
| 43 | `test_line_delete` | Select line → Delete → line card removed from DOM; line count decreases |

**Source changes:** Add `data-testid` to line-row toolbar buttons.

**Estimated size:** ~140 lines of test code, ~25 lines of source changes.

---

## Commit 7 — Toolbar: word-scope actions

**File:** `tests/browser/test_toolbar_word_actions.py` (new)

Prerequisite: select words via word checkboxes.

| Button # | Test | What it verifies |
| --- | --- | --- |
| 44 | `test_word_merge_with_selection` | Select 2 adjacent words → merge → word count in line decreases by 1; merged word text contains both |
| 45 | `test_word_refine` | Select word → click Refine → success notification; word image refreshes |
| 46 | `test_word_expand_refine` | Select word → click Expand+Refine → success notification; word image refreshes |
| 47 | `test_word_form_line` | Select words from a line → form new line → line count increases by 1; words move to new line |
| 48 | `test_word_form_paragraph` | Select words → form new paragraph → paragraph count increases by 1; words move to new paragraph |
| 49 | `test_word_copy_gt_to_ocr` | Select word → GT→OCR → word's OCR text updates to match GT value; selection cleared |
| 50 | `test_word_copy_ocr_to_gt` | Select word → OCR→GT → word's GT text updates to match OCR value; selection cleared |
| 51 | `test_word_validate` | Select word → Validate → word icon turns green; line validation count increments |
| 52 | `test_word_unvalidate` | Validate first, then Unvalidate → icon reverts to grey; validation count decrements |
| 53 | `test_word_delete` | Select word → Delete → word element removed from DOM; word count in line decreases |

**Source changes:** Add `data-testid` to word-row toolbar buttons.

**Estimated size:** ~140 lines of test code, ~25 lines of source changes.

---

## Commit 8 — Toolbar: Clear Component + Scope dropdown

**File:** `tests/browser/test_word_match.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 56 | `test_clear_component_button` | Select word → Apply Component → tag chip appears; Clear Component → tag chip removed from DOM |
| 104 | `test_scope_dropdown_interaction` | Open Scope dropdown → select "Whole" → dropdown shows selected value; select "Part" → value updates |

**Estimated size:** ~40 lines.

---

## Commit 9 — Word Edit Dialog: header and style controls

**File:** `tests/browser/test_word_edit_dialog.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 65 | `test_dialog_apply_and_close` | Edit GT text → click checkmark → dialog closes; word in main grid shows updated GT text |
| 66 | `test_dialog_close_without_saving` | Edit GT text → click X → dialog closes; word in main grid retains original GT text |
| 67 | `test_dialog_apply_style` | Click Apply Style in dialog → tag chip appears; close dialog → word in grid shows style indicator |
| 69 | `test_dialog_clear_component` | Apply Component → chip appears; Clear Component → chip count drops to 0 |

**Estimated size:** ~70 lines.

---

## Commit 10 — Word Edit Dialog: merge / split / delete

**File:** `tests/browser/test_word_edit_dialog.py` (extend)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 71 | `test_dialog_merge_prev` | Click Merge Prev → dialog refreshes with merged text; close → word count in line decreases by 1 |
| 72 | `test_dialog_merge_next` | Click Merge Next → dialog refreshes with merged text; close → word count in line decreases by 1 |
| 73 | `test_dialog_split_horizontal` | Click in word image to place marker → click H split → dialog shows first half; close → word count increases by 1 |
| 74 | `test_dialog_split_vertical` | Click in word image to place marker → click V split → dialog shows top portion; close → word count increases by 1 |
| 75 | `test_dialog_delete_word` | Click Delete → dialog closes; word element removed from line in main grid |

**Source changes:** Add `data-testid` to merge/split/delete buttons in
`word_edit_dialog.py`.

**Estimated size:** ~100 lines of test code, ~10 lines of source changes.

---

## Commit 11 — Word Edit Dialog: bbox cropping

**File:** `tests/browser/test_word_edit_dialog.py` (extend)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 76 | `test_dialog_crop_above` | Place horizontal marker → click Crop Above → preview image updates showing cropped bbox |
| 77 | `test_dialog_crop_below` | Place horizontal marker → click Crop Below → preview image updates showing cropped bbox |
| 78 | `test_dialog_crop_left` | Place vertical marker → click Crop Left → preview image updates showing cropped bbox |
| 79 | `test_dialog_crop_right` | Place vertical marker → click Crop Right → preview image updates showing cropped bbox |

**Estimated size:** ~60 lines.

---

## Commit 12 — Word Edit Dialog: bbox refine + nudge + apply/reset

**File:** `tests/browser/test_word_edit_dialog.py` (extend)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 80 | `test_dialog_refine_preview` | Click Refine → preview image src changes to show refined bbox |
| 81 | `test_dialog_expand_refine_preview` | Click Expand+Refine → preview image src changes to show expanded+refined bbox |
| 82-89 | `test_dialog_nudge_buttons` | Click each of 8 nudge buttons → preview image src changes after each click; all directions work |
| 90 | `test_dialog_reset_nudges` | Nudge then Reset → preview image reverts to original src |
| 91 | `test_dialog_apply_nudges` | Nudge then Apply → dialog closes; word image in main grid shows updated bbox |
| 92 | `test_dialog_apply_and_refine_nudges` | Nudge then Apply+Refine → dialog closes; word image in main grid shows refined bbox |

**Source changes:** Add `data-testid` to nudge/apply/reset buttons in
`word_edit_dialog.py`.

**Estimated size:** ~120 lines of test code, ~20 lines of source changes.

---

## Commit 13 — Source folder dialog

**File:** `tests/browser/test_source_folder_dialog.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 2 | `test_folder_icon_opens_dialog` | Click folder icon → dialog element appears in DOM with "Source Projects Folder" heading |
| 3 | `test_dialog_home_button` | Click Home → path label updates to home directory; folder listing refreshes |
| 4 | `test_dialog_up_button` | Click Up → path label changes to parent directory; folder listing refreshes with parent contents |
| 5 | `test_dialog_open_typed_path` | Type valid path in input → click Open → path label updates to typed path; listing shows contents |
| 6 | `test_dialog_use_current` | Click Use Current → path input populated with current source folder path |
| 7 | `test_dialog_cancel` | Click Cancel → dialog closes; project dropdown options unchanged from before |
| 8 | `test_dialog_apply` | Navigate to valid folder → Apply → dialog closes; project dropdown options update to new folder's projects |
| 9 | `test_dialog_enter_in_path_input` | Type path + press Enter → path label updates; folder listing refreshes (same as Open Typed Path) |

**Estimated size:** ~120 lines.

---

## Commit 14 — Keyboard shortcuts + GT editing

**File:** `tests/browser/test_keyboard_shortcuts.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 13 | `test_enter_in_page_input_navigates` | Fill page input with "3" + press Enter → URL updates to page/3; page content refreshes |
| 93 | `test_enter_in_gt_input_commits` | Edit GT text in word edit dialog + press Enter → GT text saved; input loses focus |
| 108 | `test_gt_text_input_edit` | Click GT field in inline editor → type new text → field value persists after clicking away |

**Estimated size:** ~60 lines.

---

## Commit 15 — Remaining interactive controls

**File:** `tests/browser/test_image_tabs.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 96 | `test_show_lines_checkbox_toggle` | Uncheck Show Lines → line overlay rectangles disappear from SVG; re-check → rectangles reappear |
| 97 | `test_show_words_checkbox_toggle` | Uncheck Show Words → word overlay rectangles disappear from SVG; re-check → rectangles reappear |
| 98 | `test_selection_mode_radio_buttons` | Click each mode (Paragraph/Line/Word) → corresponding checkboxes appear/disappear in word match list; toolbar buttons enable/disable accordingly |

**Estimated size:** ~50 lines.

---

## Summary

| Commit | Area | New Tests | Cumulative Coverage |
| --- | --- | --- | --- |
| 1 | Page actions | 4 | 23% |
| 2 | Line card buttons | 5 | 28% |
| 3 | Word buttons | 3 | 31% |
| 4 | Toolbar — page scope | 6 | 36% |
| 5 | Toolbar — paragraph scope | 9 | 45% |
| 6 | Toolbar — line scope | 11 | 55% |
| 7 | Toolbar — word scope | 10 | 64% |
| 8 | Toolbar — clear/scope | 2 | 66% |
| 9 | Dialog — header/style | 4 | 70% |
| 10 | Dialog — merge/split/delete | 5 | 74% |
| 11 | Dialog — bbox crop | 4 | 78% |
| 12 | Dialog — refine/nudge/apply | 6 | 84% |
| 13 | Source folder dialog | 8 | 91% |
| 14 | Keyboard shortcuts | 3 | 94% |
| 15 | Image tab controls | 3 | 97% |
| **Total** | | **83 new tests** | **97%** |

Remaining 3% is display-only elements (page name, stats label, loading
overlay) already covered by existing visibility checks.
