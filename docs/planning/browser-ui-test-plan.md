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
| 14 | `test_reload_ocr_button_click` | Click Reload OCR → notification appears |
| 16 | `test_load_page_button_click` | Click Load Page → notification appears |
| 17 | `test_rematch_gt_button_present` | Rematch GT button visible after load |
| 17 | `test_rematch_gt_button_click` | Click Rematch GT → notification appears |

**Estimated size:** ~50 lines of new test code.

---

## Commit 2 — Per-line action buttons (renderer line cards)

**File:** `tests/browser/test_word_match_line_actions.py` (new)

Requires: `data-testid` attributes on line-card action buttons in
`word_match_renderer.py` (or tooltip-based selectors).

| Button # | Test | What it verifies |
| --- | --- | --- |
| 57 | `test_paragraph_expander_toggle` | Click expander → paragraph collapses/expands |
| 58 | `test_line_copy_gt_to_ocr` | Click GT→OCR on a line → no error |
| 59 | `test_line_copy_ocr_to_gt` | Click OCR→GT on a line → no error |
| 60 | `test_line_validate_toggle` | Click Validate on a line → icon changes to Unvalidate |
| 61 | `test_line_delete` | Click delete on a line → line removed from DOM |

**Source changes:** Add `data-testid` to line-card action buttons in
`word_match_renderer.py`.

**Estimated size:** ~80 lines of test code, ~10 lines of source changes.

---

## Commit 3 — Per-word buttons (validate toggle, tag clear)

**File:** `tests/browser/test_word_match.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 63 | `test_word_validate_toggle` | Click validate icon → word marked validated |
| 64 | `test_word_tag_clear_in_renderer` | Clear tag chip in renderer → chip removed |
| 107 | `test_line_checkbox_selection` | Check line checkbox → line selected |

**Source changes:** May need `data-testid` on word validate button if
tooltip selectors are unreliable.

**Estimated size:** ~60 lines.

---

## Commit 4 — Toolbar: page-scope actions

**File:** `tests/browser/test_toolbar_page_actions.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 18 | `test_page_refine_bboxes_present` | Refine bboxes button visible |
| 19 | `test_page_expand_refine_bboxes_present` | Expand+Refine button visible |
| 20 | `test_page_copy_gt_to_ocr` | Click GT→OCR (page) → notification |
| 21 | `test_page_copy_ocr_to_gt` | Click OCR→GT (page) → notification |
| 22 | `test_page_validate_all` | Click Validate all → words marked validated |
| 23 | `test_page_unvalidate_all` | Click Unvalidate all → words marked unvalidated |

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
| 24 | `test_paragraph_merge_button_present` | Merge paragraphs button visible |
| 25 | `test_paragraph_refine_present` | Refine paragraphs button visible |
| 26 | `test_paragraph_expand_refine_present` | Expand+Refine button visible |
| 27 | `test_paragraph_split_after_line_present` | Split after line button visible |
| 28 | `test_paragraph_copy_gt_to_ocr` | Click GT→OCR (paragraphs) → no error |
| 29 | `test_paragraph_copy_ocr_to_gt` | Click OCR→GT (paragraphs) → no error |
| 30 | `test_paragraph_validate` | Click Validate (paragraphs) → validated |
| 31 | `test_paragraph_unvalidate` | Click Unvalidate (paragraphs) → unvalidated |
| 32 | `test_paragraph_delete` | Click Delete (paragraphs) → paragraph removed |

**Source changes:** Add `data-testid` to paragraph-row toolbar buttons.

**Estimated size:** ~120 lines of test code, ~20 lines of source changes.

---

## Commit 6 — Toolbar: line-scope actions

**File:** `tests/browser/test_toolbar_line_actions.py` (new)

Prerequisite: select lines via line checkboxes.

| Button # | Test | What it verifies |
| --- | --- | --- |
| 33 | `test_line_merge_with_selection` | Select 2 lines → merge → count decreases |
| 34 | `test_line_refine_present` | Refine lines button visible |
| 35 | `test_line_expand_refine_present` | Expand+Refine button visible |
| 36 | `test_line_split_after_word_present` | Split after word button visible |
| 37 | `test_line_split_by_selection_present` | Split by selection button visible |
| 38 | `test_line_form_paragraph_present` | Form new paragraph button visible |
| 39 | `test_line_copy_gt_to_ocr` | Click GT→OCR (lines) → no error |
| 40 | `test_line_copy_ocr_to_gt` | Click OCR→GT (lines) → no error |
| 41 | `test_line_validate` | Click Validate (lines) → validated |
| 42 | `test_line_unvalidate` | Click Unvalidate (lines) → unvalidated |
| 43 | `test_line_delete` | Click Delete (lines) → line removed |

**Source changes:** Add `data-testid` to line-row toolbar buttons.

**Estimated size:** ~140 lines of test code, ~25 lines of source changes.

---

## Commit 7 — Toolbar: word-scope actions

**File:** `tests/browser/test_toolbar_word_actions.py` (new)

Prerequisite: select words via word checkboxes.

| Button # | Test | What it verifies |
| --- | --- | --- |
| 44 | `test_word_merge_with_selection` | Select 2 words → merge → count decreases |
| 45 | `test_word_refine_present` | Refine words button visible |
| 46 | `test_word_expand_refine_present` | Expand+Refine button visible |
| 47 | `test_word_form_line_present` | Form new line button visible |
| 48 | `test_word_form_paragraph_present` | Form new paragraph button visible |
| 49 | `test_word_copy_gt_to_ocr` | Click GT→OCR (words) → no error |
| 50 | `test_word_copy_ocr_to_gt` | Click OCR→GT (words) → no error |
| 51 | `test_word_validate` | Click Validate (words) → validated |
| 52 | `test_word_unvalidate` | Click Unvalidate (words) → unvalidated |
| 53 | `test_word_delete` | Click Delete (words) → word removed |

**Source changes:** Add `data-testid` to word-row toolbar buttons.

**Estimated size:** ~140 lines of test code, ~25 lines of source changes.

---

## Commit 8 — Toolbar: Clear Component + Scope dropdown

**File:** `tests/browser/test_word_match.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 56 | `test_clear_component_button` | Select word → Apply Component → Clear Component → tag removed |
| 104 | `test_scope_dropdown_interaction` | Select Scope option → value changes |

**Estimated size:** ~40 lines.

---

## Commit 9 — Word Edit Dialog: header and style controls

**File:** `tests/browser/test_word_edit_dialog.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 65 | `test_dialog_apply_and_close` | Click checkmark → dialog closes, changes saved |
| 66 | `test_dialog_close_without_saving` | Click X → dialog closes, no changes |
| 67 | `test_dialog_apply_style` | Apply Style in dialog → tag chip appears (already partly tested) |
| 69 | `test_dialog_clear_component` | Clear Component in dialog → chip removed |

**Estimated size:** ~70 lines.

---

## Commit 10 — Word Edit Dialog: merge / split / delete

**File:** `tests/browser/test_word_edit_dialog.py` (extend)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 71 | `test_dialog_merge_prev` | Click Merge Prev → dialog closes, word count decreases |
| 72 | `test_dialog_merge_next` | Click Merge Next → dialog closes, word count decreases |
| 73 | `test_dialog_split_horizontal` | Click H split → word count increases |
| 74 | `test_dialog_split_vertical` | Click V split → word count increases |
| 75 | `test_dialog_delete_word` | Click Delete → dialog closes, word removed |

**Source changes:** Add `data-testid` to merge/split/delete buttons in
`word_edit_dialog.py`.

**Estimated size:** ~100 lines of test code, ~10 lines of source changes.

---

## Commit 11 — Word Edit Dialog: bbox cropping

**File:** `tests/browser/test_word_edit_dialog.py` (extend)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 76 | `test_dialog_crop_above` | Crop Above button visible and clickable |
| 77 | `test_dialog_crop_below` | Crop Below button visible and clickable |
| 78 | `test_dialog_crop_left` | Crop Left button visible and clickable |
| 79 | `test_dialog_crop_right` | Crop Right button visible and clickable |

**Estimated size:** ~60 lines.

---

## Commit 12 — Word Edit Dialog: bbox refine + nudge + apply/reset

**File:** `tests/browser/test_word_edit_dialog.py` (extend)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 80 | `test_dialog_refine_preview` | Click Refine → preview updates |
| 81 | `test_dialog_expand_refine_preview` | Click Expand+Refine → preview updates |
| 82-89 | `test_dialog_nudge_buttons` | All 8 nudge buttons clickable, pending state shown |
| 90 | `test_dialog_reset_nudges` | Click Reset → pending edits cleared |
| 91 | `test_dialog_apply_nudges` | Click Apply → bbox updated |
| 92 | `test_dialog_apply_and_refine_nudges` | Click Apply+Refine → bbox updated |

**Source changes:** Add `data-testid` to nudge/apply/reset buttons in
`word_edit_dialog.py`.

**Estimated size:** ~120 lines of test code, ~20 lines of source changes.

---

## Commit 13 — Source folder dialog

**File:** `tests/browser/test_source_folder_dialog.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 2 | `test_folder_icon_opens_dialog` | Click folder icon → dialog appears |
| 3 | `test_dialog_home_button` | Click Home → path resets |
| 4 | `test_dialog_up_button` | Click Up → navigates to parent |
| 5 | `test_dialog_open_typed_path` | Type path → click Open → path changes |
| 6 | `test_dialog_use_current` | Click Use Current → path populated |
| 7 | `test_dialog_cancel` | Click Cancel → dialog closes, no change |
| 8 | `test_dialog_apply` | Click Apply → source folder updated |
| 9 | `test_dialog_enter_in_path_input` | Press Enter in path input → navigates |

**Estimated size:** ~120 lines.

---

## Commit 14 — Keyboard shortcuts + GT editing

**File:** `tests/browser/test_keyboard_shortcuts.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 13 | `test_enter_in_page_input_navigates` | Press Enter in page input → page changes |
| 93 | `test_enter_in_gt_input_commits` | Press Enter in GT input → value committed |
| 108 | `test_gt_text_input_edit` | Type in GT field → value stored |

**Estimated size:** ~60 lines.

---

## Commit 15 — Remaining interactive controls

**File:** `tests/browser/test_image_tabs.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 96 | `test_show_lines_checkbox_toggle` | Click Show Lines → toggle on/off |
| 97 | `test_show_words_checkbox_toggle` | Click Show Words → toggle on/off |
| 98 | `test_selection_mode_radio_buttons` | Click each selection mode → value changes |

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
