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

### Standard tests per button

The tables below focus on **action + state-change verification** — the
hardest tests to get right. These are **not the only tests** per button.
Every button should also have the following standard tests where
applicable:

| Category | Test pattern | Example |
| --- | --- | --- |
| **Presence** | Button visible after page/dialog loads | `assert button.is_visible()` |
| **Label / icon** | Correct text, icon name, or tooltip | `assert button.get_attribute("aria-label") == "Reload OCR"` |
| **Disabled state** | Disabled when preconditions unmet (no selection, no project) | `assert button.is_disabled()` |
| **Enabled state** | Enabled once preconditions met | Select item → `assert not button.is_disabled()` |
| **Accessibility** | Has `aria-label` or visible text for screen readers | `assert button.get_attribute("aria-label")` |

Each commit section notes additional standard tests alongside the action
tests.

---

## Commit 1 — Page Actions: interaction tests for untested buttons

**File:** `tests/browser/test_page_actions.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 14 | `test_reload_ocr_button_click` | Read first word's OCR label text → click Reload OCR → wait for success notification → OCR label for first word still present (page re-rendered); GT input values preserved (not cleared) |
| 16 | `test_load_page_button_click` | Read first word's GT input value → click Load Page → wait for success notification → GT input values restored from saved JSON; validation icons reflect saved state |
| 17 | `test_rematch_gt_button_present` | Rematch GT button visible with tooltip after project load |
| 17 | `test_rematch_gt_button_click` | Edit a word's GT input to "XYZZY" → click Rematch GT → wait for success notification → GT input reverts to source-matched text (no longer "XYZZY"); validation cleared for that word (icon grey) |

**Also include:**

- `test_reload_ocr_button_present` — visible with correct icon/tooltip after project load.
- `test_save_page_button_present` — visible; already tested for click in existing suite.
- `test_load_page_button_present` — visible with correct label.
- `test_rematch_gt_button_disabled_without_project` — disabled on home page (no project loaded).

**Estimated size:** ~80 lines of new test code.

---

## Commit 2 — Per-line action buttons (renderer line cards)

**File:** `tests/browser/test_word_match_line_actions.py` (new)

Requires: `data-testid` attributes on line-card action buttons in
`word_match_renderer.py` (or tooltip-based selectors).

| Button # | Test | What it verifies |
| --- | --- | --- |
| 57 | `test_paragraph_expander_toggle` | Click expander → paragraph body collapses (hidden); click again → body re-appears |
| 58 | `test_line_copy_gt_to_ocr` | Read OCR label and GT input for first word (expect mismatch) → click GT→OCR → OCR label text now equals the previous GT value; match status icon changes to exact |
| 59 | `test_line_copy_ocr_to_gt` | Read OCR label and GT input for first word → click OCR→GT → GT input value now equals the OCR label text; validation icons reset to grey |
| 60 | `test_line_validate_toggle` | Count validate buttons with color=grey in line → click Validate → buttons now color=green; line header validated count matches word count; click Unvalidate → buttons revert to grey; header count shows 0 |
| 61 | `test_line_delete` | Count line cards before → click delete → count decreases by 1; deleted line's words no longer present in DOM |

**Source changes:** Add `data-testid` to line-card action buttons in
`word_match_renderer.py`.

**Also include:**

- `test_line_action_buttons_present` — GT→OCR, OCR→GT, Validate, Delete buttons visible on every line card.
- `test_paragraph_expander_icon` — correct expand/collapse icon state.
- `test_line_delete_confirmation` — if a confirm dialog shows, verify it can be cancelled (no deletion).

**Estimated size:** ~120 lines of test code, ~10 lines of source changes.

---

## Commit 3 — Per-word buttons (validate toggle, tag clear)

**File:** `tests/browser/test_word_match.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 63 | `test_word_validate_toggle` | Assert validate button has color=grey → click → assert color=green; click again → assert color=grey; stats label validated count increments then decrements |
| 64 | `test_word_tag_clear_in_renderer` | Hover tag chip → clear button appears; click clear → chip element removed from DOM |
| 107 | `test_line_checkbox_selection` | Check line checkbox → line-scope toolbar buttons become enabled; uncheck → buttons disable |

**Source changes:** May need `data-testid` on word validate button if
tooltip selectors are unreliable.

**Also include:**

- `test_word_validate_button_present` — validate icon visible on each word column.
- `test_word_tag_chip_present` — tag chip visible when word has tags; absent when no tags.
- `test_line_checkbox_present` — checkbox visible in each line card header.

**Estimated size:** ~100 lines.

---

## Commit 4 — Toolbar: page-scope actions

**File:** `tests/browser/test_toolbar_page_actions.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 18 | `test_page_refine_bboxes_click` | Record word image src values → click Refine → success notification "Bounding boxes refined"; at least one word image src differs from recorded value |
| 19 | `test_page_expand_refine_bboxes_click` | Record word image src values → click Expand+Refine → success notification "expanded and refined"; at least one word image src differs from recorded value |
| 20 | `test_page_copy_gt_to_ocr` | Read first word's OCR label and GT input → click GT→OCR (page) → OCR label now matches previous GT value for every word; all match status icons become exact |
| 21 | `test_page_copy_ocr_to_gt` | Read first word's OCR label and GT input → click OCR→GT (page) → every GT input value now equals its OCR label text; all validation icons reset to grey |
| 22 | `test_page_validate_all` | Count word validate buttons with color=grey → click Validate all → all validate buttons now have color=green; stats label count equals total word count |
| 23 | `test_page_unvalidate_all` | Validate all first → confirm all green; click Unvalidate all → all validate buttons revert to color=grey; stats label shows 0 validated |

**Source changes:** Add `data-testid` to page-row toolbar buttons in
`word_match_toolbar.py`.

**Also include:**

- `test_page_scope_buttons_present` — all 6 page-scope buttons visible in toolbar after project load.
- `test_page_scope_buttons_have_tooltips` — each button has a descriptive tooltip/aria-label.

**Estimated size:** ~120 lines of test code, ~15 lines of source changes.

---

## Commit 5 — Toolbar: paragraph-scope actions

**File:** `tests/browser/test_toolbar_paragraph_actions.py` (new)

Prerequisite: select a paragraph (expand paragraph → check line checkboxes
or word checkboxes within it).

| Button # | Test | What it verifies |
| --- | --- | --- |
| 24 | `test_paragraph_merge` | Count paragraphs → count lines in each → select 2 adjacent paragraphs → merge → paragraph count decreases by 1; remaining paragraph contains combined line count |
| 25 | `test_paragraph_refine` | Select paragraph → record word image src values → click Refine → success notification; at least one word image src differs from recorded value |
| 26 | `test_paragraph_expand_refine` | Select paragraph → record word image src values → click Expand+Refine → success notification; at least one word image src differs from recorded value |
| 27 | `test_paragraph_split_after_line` | Count paragraphs → count lines in paragraph → select a line → split → paragraph count increases by 1; lines below selected line appear in new paragraph |
| 28 | `test_paragraph_copy_gt_to_ocr` | Select paragraph → read OCR/GT values → click GT→OCR → OCR labels now equal previous GT values; match status icons become exact; selection checkboxes cleared |
| 29 | `test_paragraph_copy_ocr_to_gt` | Select paragraph → read OCR/GT values → click OCR→GT → GT inputs now equal OCR label text; validation icons reset to grey; selection checkboxes cleared |
| 30 | `test_paragraph_validate` | Select paragraph → count validate buttons with color=grey → Validate → all buttons now color=green; line header validated counts equal word counts |
| 31 | `test_paragraph_unvalidate` | Validate first → confirm all green; Unvalidate → all buttons revert to color=grey; line header validated counts show 0 |
| 32 | `test_paragraph_delete` | Count paragraphs → read line texts in target paragraph → select → Delete → paragraph count decreases by 1; deleted paragraph's line texts no longer present in DOM |

**Source changes:** Add `data-testid` to paragraph-row toolbar buttons.

**Also include:**

- `test_paragraph_scope_buttons_disabled_without_selection` — all paragraph-scope buttons disabled when nothing selected.
- `test_paragraph_scope_buttons_enabled_with_selection` — select a paragraph → buttons become enabled.
- `test_paragraph_scope_buttons_have_tooltips` — each button has a descriptive tooltip/aria-label.

**Estimated size:** ~160 lines of test code, ~20 lines of source changes.

---

## Commit 6 — Toolbar: line-scope actions

**File:** `tests/browser/test_toolbar_line_actions.py` (new)

Prerequisite: select lines via line checkboxes.

| Button # | Test | What it verifies |
| --- | --- | --- |
| 33 | `test_line_merge_with_selection` | Count lines in paragraph → count words in each selected line → merge → line count decreases by 1; first line now contains combined word count |
| 34 | `test_line_refine` | Select line → record word image src values → click Refine → success notification; at least one word image src differs from recorded value |
| 35 | `test_line_expand_refine` | Select line → record word image src values → click Expand+Refine → success notification; at least one word image src differs from recorded value |
| 36 | `test_line_split_after_word` | Count lines and words in line → select word in middle → split → line count increases by 1; original line has fewer words; new line has remaining words |
| 37 | `test_line_split_by_selection` | Count lines → select subset of words in line → split by selection → line count increases by 1; selected words appear in new line; unselected remain in original |
| 38 | `test_line_form_paragraph` | Count paragraphs → select lines → read their word texts → form new paragraph → paragraph count increases by 1; selected lines' words appear in new paragraph; absent from original |
| 39 | `test_line_copy_gt_to_ocr` | Select line → read OCR/GT values → click GT→OCR → OCR labels now equal previous GT values; match icons become exact; selection cleared |
| 40 | `test_line_copy_ocr_to_gt` | Select line → read OCR/GT values → click OCR→GT → GT inputs now equal OCR label text; validation icons reset to grey; selection cleared |
| 41 | `test_line_validate` | Select line → count validate buttons with color=grey → Validate → all buttons now color=green; line header validated count equals word count |
| 42 | `test_line_unvalidate` | Validate first → confirm all green; Unvalidate → all buttons revert to color=grey; line header validated count shows 0 |
| 43 | `test_line_delete` | Count lines before → select line → read its word texts → Delete → line count decreases by 1; deleted line's word texts no longer present in DOM |

**Source changes:** Add `data-testid` to line-row toolbar buttons.

**Also include:**

- `test_line_scope_buttons_disabled_without_selection` — all line-scope buttons disabled when no line selected.
- `test_line_scope_buttons_enabled_with_selection` — select a line → buttons become enabled.
- `test_line_scope_buttons_have_tooltips` — each button has a descriptive tooltip/aria-label.
- `test_line_merge_disabled_with_single_selection` — merge disabled when only 1 line selected (need 2+).

**Estimated size:** ~190 lines of test code, ~25 lines of source changes.

---

## Commit 7 — Toolbar: word-scope actions

**File:** `tests/browser/test_toolbar_word_actions.py` (new)

Prerequisite: select words via word checkboxes.

| Button # | Test | What it verifies |
| --- | --- | --- |
| 44 | `test_word_merge_with_selection` | Count words in line → read text of 2 adjacent words → select both → merge → word count decreases by 1; remaining word's OCR label contains combined text |
| 45 | `test_word_refine` | Select word → record its image src → click Refine → success notification; word image src differs from recorded value |
| 46 | `test_word_expand_refine` | Select word → record its image src → click Expand+Refine → success notification; word image src differs from recorded value |
| 47 | `test_word_form_line` | Count lines → select words → read their texts → form new line → line count increases by 1; selected words' texts appear in new line; absent from original line |
| 48 | `test_word_form_paragraph` | Count paragraphs → select words → read their texts → form new paragraph → paragraph count increases by 1; selected words' texts appear in new paragraph |
| 49 | `test_word_copy_gt_to_ocr` | Select word → read OCR label and GT input → click GT→OCR → OCR label now equals previous GT value; match icon becomes exact; selection cleared |
| 50 | `test_word_copy_ocr_to_gt` | Select word → read OCR label and GT input → click OCR→GT → GT input now equals OCR label text; validation icon resets to grey; selection cleared |
| 51 | `test_word_validate` | Select word → assert validate button color=grey → Validate → button now color=green; line header validated count increments by 1 |
| 52 | `test_word_unvalidate` | Validate first → confirm color=green; Unvalidate → button reverts to color=grey; line header validated count decrements by 1 |
| 53 | `test_word_delete` | Count words in line before → select word → read its text → Delete → word count decreases by 1; deleted word's text no longer present in line |

**Source changes:** Add `data-testid` to word-row toolbar buttons.

**Also include:**

- `test_word_scope_buttons_disabled_without_selection` — all word-scope buttons disabled when no word selected.
- `test_word_scope_buttons_enabled_with_selection` — select a word → buttons become enabled.
- `test_word_scope_buttons_have_tooltips` — each button has a descriptive tooltip/aria-label.
- `test_word_merge_disabled_with_single_selection` — merge disabled when only 1 word selected (need 2+).
- `test_word_delete_disabled_without_selection` — delete disabled when nothing selected.

**Estimated size:** ~200 lines of test code, ~25 lines of source changes.

---

## Commit 8 — Toolbar: Clear Component + Scope dropdown

**File:** `tests/browser/test_word_match.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 56 | `test_clear_component_button` | Select word → Apply Component → assert tag chip appears with component name; click Clear Component → assert tag chip removed from DOM |
| 104 | `test_scope_dropdown_interaction` | Read current scope dropdown value → open dropdown → select "Whole" → assert dropdown value shows "Whole"; select "Part" → assert value shows "Part" |

**Also include:**

- `test_clear_component_button_disabled_without_component` — disabled when word has no component tag.
- `test_scope_dropdown_present` — dropdown visible with default value after project load.

**Estimated size:** ~60 lines.

---

## Commit 9 — Word Edit Dialog: header and style controls

**File:** `tests/browser/test_word_edit_dialog.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 65 | `test_dialog_apply_and_close` | Read GT input in main grid → open dialog → change GT text to "XYZZY" → click checkmark → dialog closes; main grid GT input now shows "XYZZY" |
| 66 | `test_dialog_close_without_saving` | Read GT input value in main grid (e.g. "hello") → open dialog → change GT text to "XYZZY" → click X → dialog closes; main grid GT input still shows "hello" |
| 67 | `test_dialog_apply_style` | Count tag chips before → click Apply Style in dialog → assert new tag chip appears with style name; close dialog → main grid word shows style indicator chip |
| 69 | `test_dialog_clear_component` | Apply Component → assert chip appears; click Clear Component → assert chip removed; chip count returns to previous value |

**Also include:**

- `test_dialog_opens_on_edit_button_click` — click edit button → dialog visible with correct word data
  (GT text, OCR text, image).
- `test_dialog_header_buttons_present` — checkmark, X, Apply Style, Apply Component, Clear Component all visible.
- `test_dialog_header_button_tooltips` — each header button has correct tooltip/aria-label.

**Estimated size:** ~110 lines.

---

## Commit 10 — Word Edit Dialog: merge / split / delete

**File:** `tests/browser/test_word_edit_dialog.py` (extend)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 71 | `test_dialog_merge_prev` | Count words before → open edit dialog on second word → read its text → click Merge Prev → dialog shows combined text of both words; close → word count decreases by 1 |
| 72 | `test_dialog_merge_next` | Count words before → open edit dialog on first word → read its text → click Merge Next → dialog shows combined text; close → word count decreases by 1 |
| 73 | `test_dialog_split_horizontal` | Count words before → open edit dialog → click in word image to place marker → click H split → dialog shows left portion text; close → word count increases by 1; both halves' text present |
| 74 | `test_dialog_split_vertical` | Count words before → open edit dialog → click in word image to place marker → click V split → dialog shows top portion text; close → word count increases by 1 |
| 75 | `test_dialog_delete_word` | Count words before → read word text → open edit dialog → click Delete → dialog closes; word count decreases by 1; deleted word's text no longer in line |

**Source changes:** Add `data-testid` to merge/split/delete buttons in
`word_edit_dialog.py`.

**Also include:**

- `test_dialog_merge_prev_disabled_on_first_word` — Merge Prev disabled when editing the first word in a line.
- `test_dialog_merge_next_disabled_on_last_word` — Merge Next disabled when editing the last word in a line.
- `test_dialog_split_buttons_disabled_without_marker` — H split and V split disabled until a marker is placed on the image.
- `test_dialog_merge_split_delete_buttons_present` — all 5 buttons visible in dialog.

**Estimated size:** ~150 lines of test code, ~10 lines of source changes.

---

## Commit 11 — Word Edit Dialog: bbox cropping

**File:** `tests/browser/test_word_edit_dialog.py` (extend)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 76 | `test_dialog_crop_above` | Record preview image src → place horizontal marker → click Crop Above → preview image src differs from original (top portion removed) |
| 77 | `test_dialog_crop_below` | Record preview image src → place horizontal marker → click Crop Below → preview image src differs from original (bottom portion removed) |
| 78 | `test_dialog_crop_left` | Record preview image src → place vertical marker → click Crop Left → preview image src differs from original (left portion removed) |
| 79 | `test_dialog_crop_right` | Record preview image src → place vertical marker → click Crop Right → preview image src differs from original (right portion removed) |

**Also include:**

- `test_dialog_crop_buttons_present` — Crop Above, Crop Below, Crop Left, Crop Right all visible.
- `test_dialog_crop_buttons_disabled_without_marker` — crop buttons disabled until a marker is placed.

**Estimated size:** ~90 lines.

---

## Commit 12 — Word Edit Dialog: bbox refine + nudge + apply/reset

**File:** `tests/browser/test_word_edit_dialog.py` (extend)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 80 | `test_dialog_refine_preview` | Record preview image src → click Refine → preview image src differs from original (bbox recomputed) |
| 81 | `test_dialog_expand_refine_preview` | Record preview image src → click Expand+Refine → preview image src differs from original |
| 82-89 | `test_dialog_nudge_buttons` | Record preview image src → click X+ → src changes; click X- → src changes back; repeat for all 8 directions |
| 90 | `test_dialog_reset_nudges` | Record original src → nudge X+ → src changes → click Reset → src equals original again |
| 91 | `test_dialog_apply_nudges` | Record main grid word image src → nudge → Apply → dialog closes; main grid word image src differs from original |
| 92 | `test_dialog_apply_and_refine_nudges` | Record main grid word image src → nudge → Apply+Refine → dialog closes; main grid word image src differs from original |

**Source changes:** Add `data-testid` to nudge/apply/reset buttons in
`word_edit_dialog.py`.

**Also include:**

- `test_dialog_nudge_buttons_present` — all 8 direction buttons plus Reset, Apply, Apply+Refine visible.
- `test_dialog_nudge_buttons_have_labels` — each nudge button has correct directional icon/label.
- `test_dialog_reset_disabled_without_nudge` — Reset disabled when no nudges have been made.
- `test_dialog_apply_disabled_without_nudge` — Apply/Apply+Refine disabled when no nudges made.

**Estimated size:** ~180 lines of test code, ~20 lines of source changes.

---

## Commit 13 — Source folder dialog

**File:** `tests/browser/test_source_folder_dialog.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 2 | `test_folder_icon_opens_dialog` | Click folder icon → assert dialog element visible in DOM with "Source Projects Folder" heading |
| 3 | `test_dialog_home_button` | Read path label → click Home → assert path label equals home directory; folder listing items differ from previous |
| 4 | `test_dialog_up_button` | Read path label (e.g. "/a/b/c") → click Up → assert path label equals parent ("/a/b"); folder listing items refresh |
| 5 | `test_dialog_open_typed_path` | Type valid path in input → click Open → assert path label equals typed path; listing shows at least one item |
| 6 | `test_dialog_use_current` | Click Use Current → assert path input value equals the current source folder path shown in label |
| 7 | `test_dialog_cancel` | Read project dropdown options before → click Cancel → assert dialog hidden; project dropdown options unchanged |
| 8 | `test_dialog_apply` | Navigate to fixtures folder → read project dropdown options before → Apply → assert dialog hidden; project dropdown options differ from before |
| 9 | `test_dialog_enter_in_path_input` | Type valid path in input → press Enter → assert path label equals typed path; listing refreshes |

**Also include:**

- `test_folder_dialog_buttons_present` — Home, Up, Open, Use Current, Cancel, Apply all visible in dialog.
- `test_folder_dialog_buttons_disabled_states` — Apply disabled when no folder change; Open disabled when path input empty.
- `test_folder_dialog_path_input_present` — path text input visible and editable.

**Estimated size:** ~170 lines.

---

## Commit 14 — Keyboard shortcuts + GT editing

**File:** `tests/browser/test_keyboard_shortcuts.py` (new)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 13 | `test_enter_in_page_input_navigates` | Fill page input with "3" → press Enter → assert URL contains "page/3"; page content matches page 3 data (different word texts than page 1) |
| 93 | `test_enter_in_gt_input_commits` | Open word edit dialog → read GT input value → type "XYZZY" → press Enter → assert GT input now shows "XYZZY"; input loses focus |
| 108 | `test_gt_text_input_edit` | Read GT input value in inline editor → click field → clear and type "XYZZY" → click away → assert GT input shows "XYZZY" (value persists after blur) |

**Also include:**

- `test_page_input_present` — page number input visible with correct initial value.
- `test_page_input_accepts_only_valid_numbers` — entering non-numeric or out-of-range value does not navigate.

**Estimated size:** ~90 lines.

---

## Commit 15 — Remaining interactive controls

**File:** `tests/browser/test_image_tabs.py` (extend existing)

| Button # | Test | What it verifies |
| --- | --- | --- |
| 96 | `test_show_lines_checkbox_toggle` | Assert line overlay rectangles present in SVG → uncheck Show Lines → assert line overlay rectangles absent; re-check → assert line rectangles present again |
| 97 | `test_show_words_checkbox_toggle` | Assert word overlay rectangles present in SVG → uncheck Show Words → assert word overlay rectangles absent; re-check → assert word rectangles present again |
| 98 | `test_selection_mode_radio_buttons` | Click Word mode → assert word checkboxes visible in match list; click Line mode → assert word checkboxes hidden, line checkboxes visible; click Paragraph mode → assert paragraph-level checkboxes visible |

**Also include:**

- `test_show_lines_checkbox_present` — checkbox visible with correct initial checked state.
- `test_show_words_checkbox_present` — checkbox visible with correct initial checked state.
- `test_selection_mode_radio_present` — all mode options visible with correct default selection.

**Estimated size:** ~80 lines.

---

## Summary

| Commit | Area | Action Tests | Standard Tests | Total New | Cumulative Coverage |
| --- | --- | --- | --- | --- | --- |
| 1 | Page actions | 4 | 4 | 8 | 23% |
| 2 | Line card buttons | 5 | 3 | 8 | 28% |
| 3 | Word buttons | 3 | 3 | 6 | 31% |
| 4 | Toolbar — page scope | 6 | 2 | 8 | 36% |
| 5 | Toolbar — paragraph scope | 9 | 3 | 12 | 45% |
| 6 | Toolbar — line scope | 11 | 4 | 15 | 55% |
| 7 | Toolbar — word scope | 10 | 5 | 15 | 64% |
| 8 | Toolbar — clear/scope | 2 | 2 | 4 | 66% |
| 9 | Dialog — header/style | 4 | 3 | 7 | 70% |
| 10 | Dialog — merge/split/delete | 5 | 4 | 9 | 74% |
| 11 | Dialog — bbox crop | 4 | 2 | 6 | 78% |
| 12 | Dialog — refine/nudge/apply | 6 | 4 | 10 | 84% |
| 13 | Source folder dialog | 8 | 3 | 11 | 91% |
| 14 | Keyboard shortcuts | 3 | 2 | 5 | 94% |
| 15 | Image tab controls | 3 | 3 | 6 | 97% |
| **Total** | | **83** | **47** | **130 new tests** | **97%** |

Remaining 3% is display-only elements (page name, stats label, loading
overlay) already covered by existing visibility checks.
