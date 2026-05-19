# Keyboard Shortcuts: Coverage Review

Iter 39 / 2026-05-06. Deep review of keyboard-shortcut registrations
in production code vs the keys actually pressed by the browser test
suite. Pure documentation; no production or test code changed in this
iter. Successor work is queued in the ranked list at the bottom.

## Executive summary

The labeler has a small surface of keyboard shortcuts — five
`keydown.enter` handlers (page-input go-to, source-folder path Enter,
two GT-input commits, and the OCR config modal does not register one)
plus one `keydown` Tab/Shift+Tab navigation handler in the per-word
GT-input column. Browser-test coverage hits four of the five Enter
handlers directly via `.press("Enter")`, the dialog GT-input Enter is
covered, and the GT-column Tab navigation is covered only by Python
unit tests (no browser test). `Escape` is pressed in three browser
tests but always against Quasar built-in behavior (close q-menu /
close q-dialog) — none asserts on a custom Escape handler because
**no custom Escape handler exists**. Findings: (1) the GT-column Tab
browser-side test is the only real coverage gap; (2) `keydown.enter`
on the OCR config HF revision input is **not** registered, so
pressing Enter there should fall through to default form-submit
behavior — worth verifying; (3) the dialog and OCR modal both rely
implicitly on Quasar's default Escape-to-close, and a regression that
adds `persistent` to either q-dialog would silently break the
existing Escape-press tests.

## Inventory of registered shortcuts (production code)

| Key combo | Scope | Action | Source location |
| --- | --- | --- | --- |
| `Enter` | Project nav page-input | Trigger `_on_goto(page_input.value, event)` | `views/projects/project_navigation_controls.py:56-59` |
| `Enter` | Source-folder dialog path-input | `_on_source_path_enter` -> open typed path | `views/header/project_load_controls.py:64` |
| `Enter` | Per-word GT input (renderer) | `_commit_word_gt_input_change` (persist GT) | `views/projects/pages/word_match_gt_editing.py:72-81` |
| `Tab` / `Shift+Tab` | Per-word GT input (renderer) | `_handle_word_gt_keydown` -> focus prev/next | `views/projects/pages/word_match_gt_editing.py:82-87, 155-183` |
| `Enter` | Word edit dialog GT input | `_commit_word_gt_input_change` (persist GT) | `views/projects/pages/word_edit_dialog.py:1496-1503` |
| `Escape` (implicit) | Any q-dialog / q-menu | Quasar default close — no custom handler | (no registration; relies on Quasar defaults) |

That is the entire keyboard-shortcut surface. There is **no**
`ui.keyboard` global handler, no `addEventListener("keydown")` JS
shim, and no custom Escape handler anywhere in `pd_ocr_labeler/`.

## Inventory of tested shortcuts (browser tests)

| Key combo | Test | Scope under test | What's asserted |
| --- | --- | --- | --- |
| `Enter` | `test_keyboard_shortcuts.py::test_enter_in_page_input_navigates` | Project nav page-input | URL navigates to `page/2`, input echoes `2` |
| `Enter` | `test_keyboard_shortcuts.py::test_page_input_accepts_only_valid_numbers` | Project nav page-input | Filling `0` + Enter does NOT navigate to `page/0` (negative path) |
| `Enter` | `test_keyboard_shortcuts.py::test_enter_in_gt_input_commits` | Word edit dialog GT input | Filled value persists in input after Enter |
| `Enter` | `test_word_match_line_actions.py::test_line_validate_validates_all_words` (incidental) | Project nav page-input | Navigates to page 3 as test setup |
| `Enter` | `test_page_actions.py::test_rematch_gt_button_click` (incidental) | Per-word GT input | Commits GT value before pressing Rematch GT button |
| `Enter` | `test_source_folder_dialog.py::test_dialog_enter_in_path_input` | Source-folder path input | After Enter, path-label echoes typed path |
| `Escape` | `test_word_match.py::test_word_tag_clear_in_renderer` | Word edit dialog (Quasar close) | Dialog closes; chip in renderer afterwards |
| `Escape` | `test_word_edit_dialog.py::test_dialog_apply_style` | Word edit dialog (Quasar close) | Dialog closes; renderer chip materializes |
| `Escape` | `test_ocr_config_modal.py::test_ocr_config_model_selects_open_menu_and_survive_cancel` | q-menu close (Quasar built-in) | Menu hides after Escape; dialog stays open |

Python-only (no browser):

| Key combo | Test | What's asserted |
| --- | --- | --- |
| `Tab` / `Shift+Tab` | `tests/pd_ocr_labeler/views/projects/pages/test_word_match.py::test_word_gt_keydown_routes_tab_and_shift_tab` | Tab routes to `_handle_word_gt_tab_navigation` with correct `(key, reverse)` |
| Non-Tab keys | `tests/pd_ocr_labeler/views/projects/pages/test_word_match.py::test_word_gt_keydown_ignores_non_tab` | Non-Tab keys do not call the navigation routine |

## Coverage matrix

| Shortcut | Browser-test? | Python-test? | Negative / scope-disabled path? |
| --- | --- | --- | --- |
| Enter in page-input | YES (success + invalid `0`) | n/a | YES (invalid `0` does not navigate) |
| Enter in source-folder path-input | YES (success path only) | n/a | NO (no test for invalid / nonexistent path; backend `_open_typed_source_path` does have a path-not-found warning notify) |
| Enter in per-word GT input (renderer) | YES (incidental in `test_rematch_gt_button_click`) | n/a | NO (no test for an empty / unchanged value commit) |
| Tab / Shift+Tab in GT input (renderer) | **NO** | YES (Python unit) | YES Python (non-Tab key ignored) |
| Enter in word edit dialog GT input | YES (success path only) | n/a | NO (no test for empty value) |
| Escape on q-dialog | YES (incidental in 2 tests) | n/a | n/a (Quasar default; no custom handler) |
| Escape on q-menu inside dialog | YES (incidental) | n/a | n/a |

## Notable findings / risks

1. **Tab navigation is not covered by any browser test.** This is the
   single registered shortcut whose effect is *not* the trivial
   submit-on-Enter pattern — it has nontrivial logic (commit current,
   focus next/prev in reading order, edge-case at first/last word).
   Python unit tests at
   `tests/pd_ocr_labeler/views/projects/pages/test_word_match.py:2785-2820`
   cover the routing layer (`_handle_word_gt_keydown`) but not the
   end-to-end "Tab in input X moves focus to input Y" Playwright
   contract. A regression that breaks the `ui.timer(0, ...)` deferred
   focus in `_handle_word_gt_tab_navigation` (line 179-183) would
   pass all current Python tests and silently break the workflow.

2. **OCR config modal HF revision input has no registered Enter
   handler.** Compare `views/header/ocr_config_modal.py` (no
   `keydown.enter`) against `views/header/project_load_controls.py`
   (yes, on path-input). A user pressing Enter in the HF revision
   input today gets default browser/Quasar behavior, which on a
   q-dialog form is typically a no-op (no implicit submit). This is
   probably intentional — Apply has its own button — but worth
   documenting. Risk: a user would expect Enter-to-Apply by analogy
   with the path-input. **Not a coverage gap, a UX inconsistency.**

3. **All three Escape tests rely on Quasar defaults, not on
   labeler-side code.** None of the labeler q-dialogs has
   `persistent` or `no-esc-dismiss` props. A future commit that adds
   `persistent` to e.g. the OCR config dialog (a reasonable choice if
   we wanted to prevent accidental data loss) would silently break
   `test_ocr_config_model_selects_open_menu_and_survive_cancel`'s
   menu-close assertion (the q-menu would still close on Escape, but
   if the test were expanded to assert dialog-close behavior, it
   would regress invisibly). Worth a short comment in the dialog
   builders documenting the implicit contract.

4. **The negative path on the page-input Enter is the strongest
   test in the suite.** `test_page_input_accepts_only_valid_numbers`
   asserts `"page/0" not in page.url` — actively asserts the
   shortcut's *gating* logic worked, not just that the success path
   fired. The other Enter tests assert positive outcomes only. A
   regression that always navigated regardless of validation would
   pass `test_enter_in_page_input_navigates` but fail this one.

5. **No cross-platform / Cmd-vs-Ctrl handling exists in the
   codebase.** No shortcuts use modifier keys (Ctrl, Cmd, Alt)
   anywhere — only Tab and Shift+Tab. This is correct:
   `_handle_word_gt_keydown` reads `event.args.get("shiftKey")`
   directly from the JS event, so there is no platform-specific bug
   surface here. Worth noting because the iter-34 review flagged a
   `Ctrl+click` concern in selection tests that turned out
   tautological (no Ctrl+click is actually wired in the labeler —
   Quasar checkbox toggle is the selection mechanism, no custom
   modifier handling).

6. **Five of six tested shortcuts only cover the success path.**
   `test_dialog_enter_in_path_input` does not test what happens when
   Enter is pressed on a nonexistent path (production code calls
   `self._notify("Directory not found", "warning")` but no test
   asserts the notify fires); `test_enter_in_gt_input_commits` does
   not test what happens when the value is unchanged or empty;
   `test_enter_in_page_input_navigates` covers the success path but
   leans on `test_page_input_accepts_only_valid_numbers` for
   negative-path coverage.

## Ranked follow-up work

1. **Add a browser test for Tab navigation between GT inputs.**
   Highest leverage: closes the only registered shortcut without
   browser coverage, exercises a nontrivial focus-management path,
   and the Python unit tests already prove the routing layer works
   so a browser failure would isolate the focus-deferral bug.
   Sketch: render page 1 (>=2 GT inputs), focus the first input,
   `page.keyboard.press("Tab")`, assert
   `page.locator('[data-testid="gt-text-input"]').nth(1)` is the
   active focused element via `expect(...).to_be_focused()`. Repeat
   with `Shift+Tab` from the second input back to the first.
   Approximate cost: 1 iter, small additive test in
   `test_keyboard_shortcuts.py`.

2. **Negative-path test for Enter in source-folder path-input.**
   Type a nonexistent path (e.g. `/nonexistent/xyz/abc`), press
   Enter, assert (a) no navigation happened (path-label unchanged),
   (b) a `bg-warning` notification surfaces with "Directory not
   found". Closes the negative branch in
   `_open_typed_source_path` (`if not next_dir.exists() or not
   next_dir.is_dir(): self._notify("Directory not found",
   "warning")`). 1 iter, additive in `test_source_folder_dialog.py`.

3. **Document the Escape-default-close contract.** Add a short
   docstring or comment in the q-dialog builders for the OCR config
   modal, source folder dialog, word edit dialog, and export dialog
   noting that Escape close is intentionally inherited from Quasar
   defaults (no `persistent` prop) and that breaking this is a UX
   regression. Pure documentation; protects the three incidental
   Escape-press tests. Doc-only iter.

4. **(Question for the human, not a test):** Should the OCR config
   modal HF revision input register a `keydown.enter` handler that
   triggers Apply? Currently inconsistent with the source-folder
   path-input. If yes, that's a small additive feature + browser
   test. If no, document the intentional asymmetry as a reply
   comment near the input definition.

5. **Lower-priority: empty / unchanged-value Enter test on the
   dialog GT input.** Filling the same value as the current value
   then Enter — currently no test asserts this is a no-op (or
   that the close-without-save behavior still works). Risk is low
   because `_commit_word_gt_input_change` is also called from the
   blur handler so the path is well-trodden, but a 5-line additive
   test would close the negative branch.

---

Risks identified: (1)-(2) above are real coverage gaps. (3) is a
silent-regression vector. (4) is a UX inconsistency, not a coverage
gap. (5) is small. The top-1 candidate (Tab navigation browser test)
is the strongest follow-up: it closes the single uncovered shortcut
in the entire codebase, has a clean Playwright `to_be_focused()`
assertion pattern, and can land additively in a single iter.
