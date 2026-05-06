# Next Step: Browser Test Coverage Expansion

**Status:** Mostly complete; mop-up phase.

Goal: close the remaining specific gaps in browser-test coverage of
UI buttons. The 14-commit phased plan in
[browser-ui-test-plan.md](browser-ui-test-plan.md) is now mostly
landed (commits 1-14 mostly checked off in that file's headings).

## Priority Order

Last refreshed: 2026-05-06 (iter 30, after landing the
in-dialog Apply-Scope dropdown-drive browser test — closes the
dialog dropdown trio (style → component → scope)).

The previous coarse "0% / 11%" rollups were obsolete — all the
top-level scope buckets are now substantially covered. What remains
is a small set of named-button gaps and a couple of follow-ups
queued by recent iterations. Items are ordered by leverage / ease.

### Real remaining gaps

1. **OCRConfigModal model-select full cancel-revert** — iter-15
   queued this: at app start (no trainer outputs discovered) the
   detection / recognition selects expose only the `huggingface`
   key, so a value-cancel-revert assertion is impossible. Needs a
   trainer-output fixture providing >=2 selectable options before a
   real value-revert test (mirroring iter-14's HF revision test) can
   land.
2. **OCRConfigModal Rescan Models** — iter-13 queued. No browser test
   for the Rescan Models button (`ocr-rescan-models-button`) yet.
   Needs the backend model-scan path to be exercisable in the browser
   fixture; iter 15 noted this is non-trivial. The sibling Apply path
   is now fully closed: iter 25 covered the no-edit round-trip smoke,
   iter 27 covered Apply-with-HF-revision-edit + persist-on-re-open.
3. ~~**`line-extract-from-selection-button` click test**~~ — **CLOSED
   in iter 21 as duplicate.** Iter 20's prompt mis-named the button:
   the actual `extract_line_from_selection_button` lives in the
   word-scope toolbar with testid `word-form-line-button`, and is
   already covered end-to-end by
   `test_word_form_line` in
   `tests/browser/test_toolbar_word_actions.py` (line 360). Iter 21
   pivoted to a deep review of the toolbar split family — see
   `docs/review-notes/2026-05-06-toolbar-split-family.md` for the
   distinct-operation analysis. Genuinely-new browser-test gaps from
   that review (multi-word and cross-line topologies for
   split-by-selection and extract-line) are queued under "Real
   remaining gaps" below as items 4-6.
4. ~~**Cross-line `split-by-selection` click test**~~ — **CLOSED in
   iter 22.** New `test_line_split_by_selection_cross_line` selects
   word 0 on line 0 and word 0 on line 1, clicks
   `line-split-by-selection-button`, and asserts `LINE_DELETE_CARD`
   delta of `+2`. The cross-line word index is computed by counting
   word-checkboxes that precede the second `line-delete-button` in
   DOM order via a small `page.evaluate` JS helper.
5. ~~**Cross-line `extract-line-from-selection` ("form-line") click
   test, +1 delta**~~ — **PIVOTED in iter 23.** Pre-flight passed
   (testid exists at `word-form-line-button`, button enables on
   cross-line selection), but the predicted `+1` delta from iter-21's
   review and the pd-book-tools unit test
   `test_split_line_with_selected_words_moves_words_into_single_new_line`
   does **not** match the running browser fixture: a cross-line
   selection of words `(0, 0)` and `(1, 0)` on a `[3, 3, 1, 5, 3, 2, 4]`
   line/word fixture produced an actual delta of `+2` (line layout
   went from `[3, 3, 1, 5, 3, 2, 4]` to `[1, 1, 2, 2, 1, 5, 3, 2, 4]`
   — the leading `[3, 3]` became `[1, 1, 2, 2]`). This is the same
   layout `line-split-by-selection-button` would produce — both
   buttons appear empirically indistinguishable on this fixture for
   cross-line two-word `(0, 0) + (1, 0)` selection. **Investigation
   needed** before this test can land: either (a) the labeler dispatch
   path differs from the unit-test path (state-layer or selection
   massaging may be reordering inputs), (b) the unit test's worked
   examples don't reflect the actual cross-line behavior on a real
   page structure, or (c) the toolbar review's `+1` worked example
   was wrong. Iter-23 deleted the failing test, pivoted to candidate 3
   (Tag-chip clear in dialog), and queued this for a future iter
   gated on root-cause analysis (single Python-side unit test
   reproducing the multi-line shape, with `print()` of pre/post line
   layouts, would resolve it in one shot).
6. ~~**Multi-word same-line `split-by-selection` non-contiguous click
   test**~~ — **CLOSED in iter 24.** New
   `test_line_split_by_selection_non_contiguous` selects words 0 and 2
   of line 0 (skipping word 1), clicks
   `line-split-by-selection-button`, and asserts a `LINE_DELETE_CARD`
   delta of `+1`. The empirical delta matched iter-21's review's
   predicted `+1`: the source line splits into selected `[w_0, w_2]`
   and unselected `[w_1]` partitions for net one extra line card. Test
   uses the same `page.evaluate` line-0-word-count helper as iter 22's
   cross-line test to sanity-check the fixture has >=3 words on line 0.
7. **Investigate iter-23's `+2` discrepancy on
   `word-form-line-button` cross-line selection.** Add a
   `pd-book-tools` unit test that mirrors the live fixture's layout
   exactly (line 0 = 3 words, line 1 = 3 words, both in same
   paragraph, page has additional unrelated lines), call
   `split_line_with_selected_words([(0, 0), (1, 0)])`, and
   `print(...)` per-line word counts before/after. If the `+2`
   reproduces in the unit test, fix the docstring + review notes; if
   `+1` reproduces in the unit test, instrument the labeler-side
   dispatch (`PageState.split_line_with_selected_words` →
   `_dispatch_line_op`) to find the divergence.

### Lower-priority / queued

- ~~**Tag-chip clear in dialog**~~ — **CLOSED in iter 23.** Pre-flight
  audit found there is no parallel `dialog-clear-style-button` to
  mirror `dialog-clear-component-button`: in the dialog, styles are
  cleared *only* via the per-chip `word-edit-tag-clear-button`
  close-icon child rendered inside each `word-edit-tag-chip` (visible
  on hover). The new test
  `test_dialog_clear_style_chip` in
  `tests/browser/test_word_edit_dialog.py` exercises the only
  affordance that exists: applies a default style, hovers the new
  chip, clicks its embedded clear icon, asserts chip count drops.
- ~~**Apply-Style select wiring inside dialog**~~ — **CLOSED in
  iter 28.** New `test_dialog_apply_style_via_dropdown` in
  `tests/browser/test_word_edit_dialog.py` clicks the
  `dialog-style-select` q-select wrapper, picks "Italics" (a
  non-default value; the default preselected style is "All Caps"
  since `WordOperations.supported_styles` returns
  `sorted(ALLOWED_TEXT_STYLE_LABELS - {"regular"})`), clicks
  `dialog-apply-style-button`, and asserts (a) chip-count went from
  baseline+0 to baseline+1 via `expect(...).to_have_count(...)` and
  (b) the chip text is "Italics" (so the dropdown selection
  drove the apply, not the default). Cleanup hovers the chip and
  clicks its embedded `word-edit-tag-clear-button` to remove the
  style, restoring baseline state.
- ~~**Apply-Component select wiring inside dialog**~~ — **CLOSED in
  iter 29.** New `test_dialog_apply_component_via_dropdown` in
  `tests/browser/test_word_edit_dialog.py` clicks the
  `dialog-component-select` q-select wrapper, picks "Superscript" (a
  non-default value; the default preselected component is "Drop Cap"
  since `WordOperations.supported_components` returns
  `tuple(sorted(ALLOWED_COMPONENTS))`), clicks
  `dialog-apply-component-button`, and asserts (a) chip-count went
  from baseline+0 to baseline+1 via `expect(...).to_have_count(...)`
  and (b) the chip text is "Superscript". Cleanup uses the
  symmetric `dialog-clear-component-button` (the existing affordance
  for component chips) to restore baseline state.
- ~~**Apply-Scope select wiring inside dialog**~~ — **CLOSED in
  iter 30.** New `test_dialog_apply_scope_via_dropdown` in
  `tests/browser/test_word_edit_dialog.py` first applies "Italics"
  via the style dropdown (which produces chip text "Italics (Whole)"
  because `WordOperations.apply_style_to_word` hard-codes the initial
  scope to `"whole"` — see `word_operations.py` line 134-137), then
  clicks the `dialog-scope-select` q-select wrapper, picks "Part",
  and asserts the chip text now contains `(Part)` and not `(Whole)`
  per `_word_display_tag_items` line 639's
  `f"{display} ({normalized_scope.title()})"` format.  The on-change
  handler `_apply_scope_for_selected_style` fires immediately on
  dropdown selection — no separate Apply Scope button.  Closes the
  dialog dropdown trio: style (iter 28), component (iter 29), scope
  (this iter).
- **`test_load_button_prevents_multiple_clicks` flake** — known
  pre-existing flake; retry up to 3x in CI. Not a coverage gap, but
  worth fixing or marking `flaky` once we have time.

### Already well covered (was claimed 0% or 11%)

- Per-line action buttons: 11 tests in
  `tests/browser/test_word_match_line_actions.py` (GT->OCR,
  OCR->GT, Validate, Delete, expander, label-button toggle).
- Toolbar word scope: 15 tests in
  `tests/browser/test_toolbar_word_actions.py`.
- Toolbar line scope: 16 tests in
  `tests/browser/test_toolbar_line_actions.py` (now includes
  `line-split-after-word-button` click coverage as of iter 19 and
  `line-split-by-selection-button` click coverage as of iter 20).
- Toolbar paragraph scope: 13 tests in
  `tests/browser/test_toolbar_paragraph_actions.py` (now includes
  `paragraph-expand-bboxes-button` click coverage as of iter 18).
- Toolbar page scope: 8 tests in
  `tests/browser/test_toolbar_page_actions.py`.
- Word edit dialog: 31 tests in `tests/browser/test_word_edit_dialog.py`
  covering header, style (default-apply, dropdown-pick-apply, per-chip
  clear), component (default-apply, dropdown-pick-apply, clear),
  scope (dropdown-pick-apply changes chip suffix from "(Whole)" to
  "(Part)"), merge/split/delete, crop, refine, all 8 nudges, reset,
  apply, apply+refine.
- Source folder dialog: 10 tests in
  `tests/browser/test_source_folder_dialog.py`.
- Header / load controls: covered across `test_home_page.py`,
  `test_project_loading.py`, `test_browser_smoke.py`,
  `test_page_actions.py` (8 tests).
- Keyboard shortcuts: 6 tests in
  `tests/browser/test_keyboard_shortcuts.py`.
- Image tab controls: 10 tests in `tests/browser/test_image_tabs.py`.
- OCRConfigModal: 7 tests in `tests/browser/test_ocr_config_modal.py`.

## Done Criteria

- Gap 1 above closed with a dedicated click test.
- Gap 2 either landed (once backend / HF fixtures are available) or
  formally deferred to a separate plan.
- Gap 3 closed in iter 21 as duplicate of `test_word_form_line`; the
  deep review at `docs/review-notes/2026-05-06-toolbar-split-family.md`
  yielded items 4-6 as the real-coverage successors.
- `make test-browser` continues to pass reliably with `pytest -n auto`.

---

## Previously Completed Next Steps

### OCRConfigModal — Apply With HF Revision Edit Round-Trip (Iter 27, Done)

Iter 25 closed the no-edit Apply path; iter 27 closes the
edited-value Apply path for the HF revision input. Pre-flight audit
confirmed the path is safe to exercise in the browser fixture without
network or trainer-output dependencies:

- `_apply_selection` on a non-empty new revision calls
  `command_set_hf_pinned_revision` →
  `AppState.set_hf_pinned_revision` → `refresh_ocr_models(notify=True)`.
- `discover_model_options(hf_pinned_revision=...)` calls
  `fetch_hf_last_modified(revision=...)` for the pinned option, but
  the probe is wrapped in a try/except that returns `None` on any
  failure (network, ImportError, missing metadata) and never raises.
  The 5 s timeout bounds the wait; default Playwright timeout is 30 s,
  so a real probe failure (the sentinel revision does not exist on HF)
  does not crash or stall the test.
- The subsequent `command_set_selected_ocr_models` on the as-opened
  detection/recognition keys is a no-op semantically (still
  `huggingface`/`huggingface`) and succeeds at the state-mutation
  layer, closing the dialog on success.
- The `_open` handler reads
  `self.app_state_model.hf_pinned_revision or ""` on every open, so
  re-opening after Apply echoes the persisted value back into the
  input.

This iteration:

- Added `test_ocr_config_hf_revision_edit_persists_through_apply` to
  `tests/browser/test_ocr_config_modal.py`. Mirrors iter 14's
  `test_ocr_config_hf_revision_edit_reverts_on_cancel` in setup,
  swapping Cancel for Apply: opens modal, fills HF input with a
  sentinel `"test-revision-apply-sentinel"`, clicks Apply, asserts the
  Apply button hides (modal closed) within 15 s, re-opens the modal,
  asserts the input value equals the sentinel.
- Bumped `to_be_visible` timeout for the Apply close to 15 s (vs. the
  default 30 s already covers the upper bound; the explicit 15 s gives
  a clear "this should be quick" signal documenting the worst-case 5 s
  HF probe + UI tear-down).
- Updated the file's module docstring's "out of scope" list to reflect
  that Apply with HF-revision edits is now covered (only Apply with
  edited model-select values remains queued, blocked on a
  trainer-output fixture).

Pure additive — no source mutations. Targeted file passes in 14.7 s
(7 tests). Full `make ci` green on the second run; the first surfaced
the pre-existing
`test_dialog_merge_prev` flake which passed in isolation, mirroring
the known `test_load_button_prevents_multiple_clicks` flake.

### Test-Pollution Flake Fix — `test_app_state.py` xdist Resolver Failures (Iter 26, Done)

Iter 25's `make ci` run surfaced a deterministic 4-test failure cluster
in `tests/pd_ocr_labeler/state/test_app_state.py` whenever the file was
collected alongside the rest of the suite under xdist. The traceback
pinpointed pytest's dotted-path resolver in
`_pytest/monkeypatch.py:resolve` — `getattr(pd_ocr_labeler, 'state')`
fails with `AttributeError: 'module' object at pd_ocr_labeler.state has
no attribute 'state'` when monkeypatch tries to walk
`"pd_ocr_labeler.state.app_state.ModelSelectionOperations.discover_model_options"`.
Iter 26 reproduced the failure twice under `make ci`, then sidestepped
the resolver entirely by passing the imported `ModelSelectionOperations`
class object to `monkeypatch.setattr` directly:

```python
monkeypatch.setattr(
    ModelSelectionOperations, "discover_model_options", fake_discover_model_options
)
```

The class object is the same one `app_state.py` imports, so monkeypatching
its `discover_model_options` classmethod attribute is observable from both
the test and production code. Root cause of why
`pd_ocr_labeler.state` is missing as an attribute on `pd_ocr_labeler` in
the failing worker remains unresolved (an earlier speculative
`import pd_ocr_labeler.state.app_state` fix did not prevent the failure
under `make ci`), but the dotted-path-free monkeypatch makes the
question moot — a class-object monkeypatch doesn't need any package
attribute to be set.

Pure test-only fix. Two consecutive `make ci` runs after the change
confirm the 4 tests are now stable; the only remaining `make ci` failure
is the unrelated pre-existing
`test_load_button_prevents_multiple_clicks` flake (passes on retry).

### OCRConfigModal — No-Edit Apply Round-Trip Smoke (Iter 25, Done)

Iter-13 queued the Apply round-trip as out of scope because Apply
"requires HF / local model availability + state mutation". A
pre-flight audit revealed the *no-edit* Apply path is in fact safe
to exercise without any of that:

- The HF-revision setter is gated by `new_revision != previous_revision`,
  so a no-edit Apply skips it entirely (no rescan, no HF probe).
- `command_set_selected_ocr_models` ultimately calls
  `AppState.set_selected_ocr_models`, which only validates the keys
  exist in `available_ocr_models` and updates state — no model
  download, no backend probe.
- On success, the handler emits a *positive* "OCR models updated"
  notification, not a negative one — so we can assert "no
  `bg-negative` notification" without false positives.

This iteration:

- Added `test_ocr_config_apply_with_no_edits_closes_without_error` to
  `tests/browser/test_ocr_config_modal.py`. The test opens the modal,
  clicks the Apply button (`ocr-config-apply-button`) without
  changing any values, and asserts (a) the dialog's Cancel/Apply
  controls become hidden (modal closed) and (b) no
  `.q-notification.bg-negative` is present in the DOM (the failure
  path emits `"Failed to apply OCR models"` with `negative` type).
- Updated the file's module docstring's "out of scope" list to
  reflect that no-edit Apply is now covered; full Apply with edited
  values remains out of scope.

Pure additive — no source mutations. Targeted file passes in 12.3s
(6 tests); full `make ci` green on retry (915 passed). The first run
surfaced an xdist-pollution flake on
`tests/pd_ocr_labeler/state/test_app_state.py` (4 tests fail when
the `state.app_state` submodule attribute hasn't been registered on
`pd_ocr_labeler.state` by an earlier worker import — the
`monkeypatch.setattr("pd_ocr_labeler.state.app_state...")` calls
fail with `AttributeError: 'module' object at pd_ocr_labeler.state
has no attribute 'state'`); the failure does not reproduce when the
file is run standalone, even with `-n auto`. This is a pre-existing
latent flake category, distinct from but reminiscent of the known
`test_load_button_prevents_multiple_clicks` flake. Worth queueing
as a fix once we have time.

### Toolbar Line Scope — Non-Contiguous Within-Line Split-By-Selection Coverage (Iter 24, Done)

Iter-21's review identified a third distinguishing-coverage gap:
the `split_lines_into_selected_and_unselected_words` primitive does
*not* require the selected partition to be contiguous on the source
line — `{w_0, w_2}` selected on `[w_0, w_1, w_2]` should produce
`[w_0, w_2]` (selected) plus `[w_1]` (unselected), net +1 line. None
of the existing browser tests exercised this invariant: iter-19's
`split-after-word` requires *exactly one* selection (so always
contiguous), and iter-20/22's `split-by-selection` tests selected
either a single word or one word per line.

This iteration:

- Added `test_line_split_by_selection_non_contiguous` to
  `tests/browser/test_toolbar_line_actions.py`. The test selects
  word 0 and word 2 of line 0 (skipping word 1), clicks
  `line-split-by-selection-button`, and asserts a `LINE_DELETE_CARD`
  delta of `+1`. A small `page.evaluate` JS helper (mirroring
  iter-22's pattern) sanity-checks line 0 has >=3 words by counting
  word-checkboxes that precede the second `line-delete-button` in
  DOM order.
- The empirical delta matched iter-21's review's predicted `+1` —
  no review-note correction needed (contrast with iter-23's
  `word-form-line-button` cross-line `+2` discrepancy that remains
  queued).

Pure additive — no source mutations.

### Word Edit Dialog — Per-Chip Style-Clear Coverage (Iter 23, Done)

Iter 23's first candidate (cross-line `word-form-line-button` `+1`
delta test) failed the pre-flight: the predicted `+1` delta from the
iter-21 review and the pd-book-tools unit tests does not match the
live browser fixture, which produced `+2` instead — see item 5 in the
priority list for the queued investigation. Iter 23 pivoted to the
queued candidate-3 work ("Tag-chip clear in dialog").

The pre-flight audit confirmed no parallel
`dialog-clear-style-button` exists in the dialog; styles are cleared
*only* via the per-chip close-icon button rendered inside each
`word-edit-tag-chip` (visible on hover, testid
`word-edit-tag-clear-button`). The existing `test_dialog_apply_style`
test reaches the *renderer*-side chip's clear button after closing
the dialog, but no test exercised the in-dialog tag clear.

This iteration:

- Added selector constant `DIALOG_TAG_CLEAR_BUTTON` to
  `tests/browser/test_word_edit_dialog.py` with a multi-line comment
  documenting the no-parallel-button asymmetry.
- Added `test_dialog_clear_style_chip`: opens the dialog, clicks
  Apply Style (default style is preselected), asserts chip count
  rose, hovers the most-recent chip, clicks its embedded clear
  button, asserts chip count fell back below the post-apply count.

Pure additive — no source mutations. New test passes in 6.8s.

### Toolbar Line Scope — Cross-Line Split-By-Selection Coverage (Iter 22, Done)

Iter-21's review identified a load-bearing gap: `line-split-by-selection-button`
is semantically distinct from `word-form-line-button` only when the
selection spans multiple source lines, but every existing browser test
exercised the degenerate single-word single-line path with a `+1` line
delta — which both buttons satisfy.  Iter 22 closed the cross-line
`split-by-selection` gap.

This iteration:

- Added `test_line_split_by_selection_cross_line` to
  `tests/browser/test_toolbar_line_actions.py`.  The test selects word
  0 on line 0 and word 0 on line 1, clicks the button, and asserts a
  `LINE_DELETE_CARD` delta of `+2` (each affected source line splits
  into a selected + unselected pair — the per-affected-line topology
  documented in the iter-21 review at
  `docs/review-notes/2026-05-06-toolbar-split-family.md`).
- Word checkboxes are flat across line cards, so to find word 0 of
  line 1 in the global checkbox list, the test uses a small
  `page.evaluate` JS helper that counts how many word-checkboxes
  precede the second `line-delete-button` in DOM order.  That count
  equals line 0's word count, which equals the global checkbox index
  of line 1 / word 0.

Pure additive — no source mutations.  Full `make ci` green
(912 passed; one pre-existing flake on
`TestNiceGuiIntegration::test_load_button_prevents_multiple_clicks`
went green on retry, as expected).

### Toolbar Split Family Deep Review (Iter 21, Done)

Iter 21 pre-flight on the queued
`line-extract-from-selection-button` click test discovered the button
was misnamed in the iter-20 hand-off: the actual
`extract_line_from_selection_button` lives on the *word*-scope
toolbar row with testid `word-form-line-button` and is already
covered by `test_word_form_line` (an existing single-word `+1` line
delta assertion). Per the iter-21 pivot guidance, iter 21 produced a
deep review of the three split-family operations
(`split_line_after_word`, `split_lines_into_selected_and_unselected_words`,
`split_line_with_selected_words`) to confirm they are distinct
operations with different selection contracts and different output
topologies. Findings recorded at
`docs/review-notes/2026-05-06-toolbar-split-family.md`. The review
identified three new genuinely-distinct-coverage browser tests
(items 4-6 in the priority list above) as the real successor work,
which was the iter-21 product. No source mutations.

### Toolbar Line Scope — Split-By-Selection Button Coverage (Done)

`line-split-by-selection-button` (`call_split` icon) is the line-scope
toolbar button that splits each affected line into "selected words"
and "unselected words" lines.  It is wired to
`_handle_split_lines_into_selected_unselected_words` and enables when
`split_lines_into_selected_unselected_callback is not None and >= 1
word selected` (`word_match_toolbar.py` ll. 842-846).  Selectors /
disabled / enabled / tooltip coverage was already in place from
earlier iterations, but no dedicated click test existed.

This iteration:

- Added a `test_line_split_by_selection` click test that switches to
  All Lines, captures the line count, selects word 0, clicks the
  button, waits for the success Quasar notification, and asserts the
  line count increased by 1 (one line became two — selected word 0
  becomes its own line, the rest remains).  Mirrors iter-19's
  `test_line_split_after_word` exactly, swapping the button selector
  and refreshing the doctring with the relevant pd-book-tools
  unit-test reference (`TestSplitLinesIntoSelectedAndUnselected::test_split_with_valid_selection`
  on a six-word page proves `[a]` + `[b, c]` from `[a, b, c]`).

Pure additive — no source mutations.  Full `make ci` green
(911 passed).

### Toolbar Line Scope — Split-After-Word Button Coverage (Done)

`line-split-after-word-button` (`call_split` icon) is the line-scope
toolbar button that splits the selected line into two lines after
exactly one selected word.  It is wired to
`_handle_split_line_after_selected_word` and enables when
`split_line_after_word_callback is not None and exactly 1 word is
selected` (`word_match_toolbar.py` ll. 824-828).  Selectors / disabled
/ enabled / tooltip coverage was already in place from earlier
iterations, but no dedicated click test existed.

This iteration:

- Added a `test_line_split_after_word` click test that switches to
  All Lines, captures the line count, selects word 0, clicks the
  button, waits for the success Quasar notification, and asserts the
  line count increased by 1 (one line became two).  Mirrors
  `test_line_delete`'s line-count delta pattern, swapping `-1` for
  `+1`.
- The fresh-OCR fixture on page 1 of `browser-test-project` produces
  7 lines from 21 words (saved-pages JSON has 1 word per line, but
  the browser session re-OCRs because saved JSON loading is not
  triggered by the load-project flow), so word 0 reliably lands in a
  multi-word line and the split succeeds.

Pure additive — no source mutations.  Full `make ci` green.

### Toolbar Paragraph Scope — Expand BBoxes Button Coverage (Done)

`paragraph-expand-bboxes-button` (`open_in_full` icon) is the
paragraph-scope toolbar button that pads the selected paragraph's
bounding boxes without running a full refine pass. It is wired to
`_handle_expand_bbox_selected_paragraphs` and shares the same enable
invariant as Refine / Expand+Refine
(`expand_paragraph_bboxes_callback is not None and >= 1 paragraph
selected`), but had **zero** browser test coverage — it was missing
from `ALL_PARA_BUTTONS` in
`tests/browser/test_toolbar_paragraph_actions.py`, absent from the
enabled-with-selection assertion list, missing from the tooltip
table, and had no click test. Symmetric mirror of iter-16's
line-scope chunk.

This iteration:

- Added `PARA_EXPAND_BBOXES` selector constant.
- Added it to `ALL_PARA_BUTTONS` so
  `test_paragraph_scope_buttons_disabled_without_selection` now covers it.
- Added it to the enabled-with-selection assertion list in
  `test_paragraph_scope_buttons_enabled_with_selection`.
- Added a tooltip-row entry (`"Expand selected paragraph bboxes"`) to
  `test_paragraph_scope_buttons_have_tooltips`.
- Added a dedicated `test_paragraph_expand_bboxes` click test that
  selects paragraph 0, clicks the button, and asserts a Quasar
  notification fires (mirroring `test_paragraph_refine` /
  `test_paragraph_expand_refine`).

Pure additive — no source mutations. Full `make ci` green
(909 passed).

### Toolbar Line Scope — Expand BBoxes Button Coverage (Done)

`line-expand-bboxes-button` (`open_in_full` icon) is the line-scope
toolbar button that pads the selected line's bounding boxes without
running a full refine pass.  It is wired to
`_handle_expand_bbox_selected_lines` and shares the same enable
invariant as Refine / Expand+Refine
(`expand_line_bboxes_callback is not None and >= 1 line selected`),
but had **zero** browser test coverage — it was missing from
`ALL_LINE_BUTTONS` in `tests/browser/test_toolbar_line_actions.py`,
absent from the enabled-with-selection assertion list, missing from
the tooltip table, and had no click test.

This iteration:

- Added `LINE_EXPAND_BBOXES` selector constant.
- Added it to `ALL_LINE_BUTTONS` so
  `test_line_scope_buttons_disabled_without_selection` now covers it.
- Added it to the enabled-with-selection assertion list in
  `test_line_scope_buttons_enabled_with_selection`.
- Added a tooltip-row entry (`"Expand selected line bboxes"`) to
  `test_line_scope_buttons_have_tooltips`.
- Added a dedicated `test_line_expand_bboxes` click test that
  selects line 0, clicks the button, and asserts a Quasar
  notification fires (mirroring `test_line_refine` /
  `test_line_expand_refine`).

Pure additive — no source mutations.  Full `make ci` green
(908 passed).

### OCR Configuration Modal — Detection/Recognition Select Cancel-Cycle Browser Test (Done)

Iter-15 follow-up to iter-14's HF revision cancel-revert test. The
modal's `_open` handler also unconditionally resets each select's value
to the canonical `selected_ocr_*_model_key` on every open
(`ocr_config_modal.py:113-128`), but at app start (no trainer outputs
discovered) the `huggingface` key is the *only* registered option, so
the UI cannot meaningfully change the value to a second one and assert
revert. The new test
`test_ocr_config_model_selects_open_menu_and_survive_cancel` asserts
the still-meaningful weaker invariants:

- Clicking each testid'd select wrapper opens a Quasar `q-menu` with at
  least one selectable `.q-item` (proves wiring is intact and `_open`
  did not crash on selects).
- After dismissing each menu via Escape, then Cancel + re-open of the
  parent modal, both select wrappers remain visible (proves the reset
  path is idempotent and Cancel doesn't corrupt select state).

Same fixture/helper/file as iter-13/14; pure additive. Queued: a full
value cancel-revert mirroring iter-14 once a trainer-output fixture
provides ≥2 selectable options.

### OCR Configuration Modal — HF Revision Cancel-Revert Browser Test (Done)

Follow-up to the iter-13 OCRConfigModal smoke tests: a fourth test
`test_ocr_config_hf_revision_edit_reverts_on_cancel` covers the
form-state preservation contract guaranteed by `_open` in
`ocr_config_modal.py:129-133`, which unconditionally resets the HF
revision input value to `app_state_model.hf_pinned_revision or ""` on
every open. The test types a sentinel into the input, presses Cancel,
re-opens the modal, and asserts the input reverted to its as-opened
baseline (`input_value()` snapshot). Same fixture / helper / file as
the iter-13 tests; pure additive coverage, no source mutations. Out of
scope and queued: editing the detection / recognition selects, Rescan
Models flow, full Apply round-trip with HF probe.

### OCR Configuration Modal — First Browser Tests (Done)

The OCR Configuration modal had a full `data-testid` contract since
`eb2a41f` but zero browser regression coverage. A new test file
`tests/browser/test_ocr_config_modal.py` adds three smoke tests using
the existing testid selectors:

- `test_ocr_config_trigger_button_present` — asserts the `tune` icon
  trigger is visible in the header at app start (no project loaded
  required, since the modal is built alongside other always-mounted
  ProjectLoadControls children).
- `test_ocr_config_modal_opens_on_trigger_click` — clicks the trigger
  and asserts the load-bearing dialog children (`ocr-config-cancel`,
  `ocr-config-apply`, `ocr-rescan-models`, `ocr-hf-revision-input`)
  become visible.
- `test_ocr_config_cancel_closes_modal` — clicks Cancel and asserts
  the same dialog children become hidden.

Visibility assertions use the q-dialog's testid'd descendants (the
Cancel / Apply buttons rendered inside the dialog body) rather than
the dialog wrapper itself, mirroring the pattern from
`tests/browser/test_source_folder_dialog.py`. Out of scope for this
chunk and queued for follow-up: Rescan Models (needs backend
model-scan path), Apply (needs HF / local model availability + state
mutation), and editing the HF revision input or model selects.

### Stable data-testid Backfill — Word Match Renderer Paragraph Label Button (Done)

The paragraph label button rendered next to the chevron expander in
`word_match_renderer.py` (the wide clickable `flat dense no-caps`
button that displays the paragraph label and shares the same
`_toggle_paragraph_expanded` handler) now exposes a stable
`data-testid` prop:

- `paragraph-label-button` — the label-text button. Useful for
  asserting the alternate paragraph toggle target (the label, not
  the chevron) is reachable, and for distinguishing it from
  `paragraph-expander-button` in tests that need to click a
  specific one of the two toggle entry points.

A new browser regression test
`tests/browser/test_word_match_line_actions.py::test_paragraph_label_button_present_and_toggles`
asserts the label button materializes, clicking it collapses the
paragraph body (line-card count drops), and clicking again restores
the original count — matching the contract of the existing chevron
expander tests. New selector constant `PARAGRAPH_LABEL` added to the
selectors block at the top of the file. Architecture doc
`docs/architecture/ui-action-buttons.md` Paragraph Expander table
updated to include a `data-testid` column and a row 57b for the
label button alongside the existing chevron entry.

### Stable data-testid Backfill — Project Navigation Page Input + Total Label (Done)

The page-number `ui.number` input and the `/ N` total-count `ui.label`
in `ProjectNavigationControls` now expose `data-testid` props
(`nav-page-input` and `nav-page-total-label`). This finishes the nav
toolbar contract started in iter 2 (Prev/Next/Go-to). All browser
tests that selected the page input via `get_by_label("Page")` and the
helpers `wait_for_page_number` / `navigate_to_page` /
`get_current_page_number` / `get_page_total_text` migrated to the
testid selectors. A new browser regression test
`tests/browser/test_keyboard_shortcuts.py::test_page_total_label_present`
asserts the total label is reachable via testid and matches `/ N`.
Architecture doc `docs/architecture/ui-action-buttons.md` updated with
a paragraph after the navigation table to record the new testids.

### Stable data-testid Backfill — Word Edit Dialog Header Label (Done)

The Word Edit Dialog's header text label ("Edit Line N, Word M") at
the top of the dialog now exposes a stable `data-testid` so browser
tests can assert the dialog opened on the intended word without
scraping visible text via a regex match over the whole dialog body:

- `dialog-header-label` — the `ui.label()` rendered at the top of the
  dialog card. Useful for asserting the dialog opened on the
  correct line/word indices, e.g. by reading the label text and
  parsing the indices, or by `to_have_text(re.compile(r"..."))`.

Existing browser test
`tests/browser/test_word_edit_dialog.py::test_dialog_opens_on_edit_button_click`
migrated from a `dialog.locator("text=/Edit Line \d+, Word \d+/")`
regex against arbitrary dialog text to a scoped
`dialog.locator(DIALOG_HEADER_LABEL).to_have_text(re.compile(...))`
assertion. New selector constant `DIALOG_HEADER_LABEL` added to the
selectors block at the top of the file. Architecture doc
`docs/architecture/ui-action-buttons.md` updated with a paragraph
beneath the existing Dialog Header table to record the new label
testid alongside the existing check / close icon-button entries.

### Stable data-testid Backfill — Word Edit Dialog Preview Columns (Done)

The three side-by-side preview columns at the top of the Word Edit
Dialog (Previous / Current / Next word) now expose stable
`data-testid` props on their wrapping `ui.column()` containers:

- `dialog-previous-preview-column` — wraps the Previous-word preview
  (rendered by `_render_word_preview`); always present, displays
  "No word" caption when the active word is the first in its line.
- `dialog-current-preview-column` — wraps the Current-word interactive
  image, GT input, zoom toggle, OCR text label, and tag-chip slot.
  Useful for scoping queries that should target the active word's
  controls without matching the Previous / Next columns.
- `dialog-next-preview-column` — wraps the Next-word preview (also via
  `_render_word_preview`); behaves symmetrically with the Previous
  column.

The shared `_render_word_preview` helper now derives its testid from
the title (`dialog-{title.lower()}-preview-column`), so both Previous
and Next columns get tagged from the same call site. A new browser
regression test
`tests/browser/test_word_edit_dialog.py::test_dialog_preview_columns_present`
asserts all three column wrappers materialize with their expected
caption labels and that the Current column scopes to the GT input
(sanity-check that the right wrapper is tagged). New selector
constants `DIALOG_PREVIOUS_PREVIEW_COLUMN`,
`DIALOG_CURRENT_PREVIEW_COLUMN`, and `DIALOG_NEXT_PREVIEW_COLUMN`
added to the selectors block at the top of the file. Architecture doc
`docs/architecture/ui-action-buttons.md` updated with a paragraph
beneath the existing tag-chip / zoom-toggle prose to record the new
preview-column testids.

### Stable data-testid Backfill — Word Match Renderer Tag-Chip Row (Done)

The renderer's per-word tag chip area in `word_match_renderer.py`
(`_create_ocr_text_cell`, ~lines 1005-1051) now exposes a stable
`data-testid` on the wrapping `ui.row()` that materializes only when
at least one chip is present:

- `word-tag-chips-row` — the outer row container, mirroring the
  dialog-side `dialog-tag-chips-row` contract added in the prior
  iteration. Useful for asserting that the chip-row materialized
  immediately after a toolbar Apply Style / Apply Component click
  (no view switch needed) and for scoping chip-count assertions to
  one specific word's row.

A new browser regression test
`tests/browser/test_word_match.py::test_word_tag_chips_row_materializes_with_chip`
asserts the chip-row container appears with the chip nested inside
it. Two new selector constants `WORD_TAG_CHIPS_ROW` and
`WORD_TAG_CHIP` were added to the selectors block at the top of
`tests/browser/test_word_match.py`. Architecture doc
`docs/architecture/ui-action-buttons.md` updated with a paragraph
beneath the per-word Tag Chip Clear Buttons table to record the new
testid alongside the existing `word-tag-chip` and
`word-tag-clear-button` entries.

### Stable data-testid Backfill — Word Edit Dialog Tag-Chip Area + Zoom Toggle (Done)

The Word Edit Dialog tag-chip region's surrounding containers and the
current-image zoom toggle now expose stable `data-testid` props:

- `dialog-tag-chips-slot` — the always-present `ui.column()` slot
  beneath the current-word image. Exists even when the active word
  has no tags, so tests can `wait_for` / scope queries to it without
  depending on chip presence.
- `dialog-tag-chips-row` — the inner `ui.row()` rendered by
  `_render_tag_chips()` only when at least one tag chip is present.
  Useful for asserting the chips row materialized after an
  apply-style / apply-component click.
- `dialog-current-zoom-toggle` — the 1x/2x/5x/10x zoom selector for
  the current-word interactive image (previously selectable only by
  the visible label text "1x"/"2x"/etc.).

Existing browser tests in `tests/browser/test_word_edit_dialog.py`
that counted chips via the legacy `.word-edit-tag-chip` CSS-class
selector (`test_dialog_apply_style`, `test_dialog_clear_component`)
migrated to `[data-testid="word-edit-tag-chip"]`. New constants
`DIALOG_TAG_CHIPS_SLOT`, `DIALOG_TAG_CHIPS_ROW`, `DIALOG_TAG_CHIP`,
and `DIALOG_CURRENT_ZOOM_TOGGLE` added to the selectors block at the
top of the file. Architecture doc
`docs/architecture/ui-action-buttons.md` updated to document the new
tag-chip-area and zoom-toggle testids alongside the existing chip
clear button entry.

### Stable data-testid Backfill — Word Edit Dialog Selects, GT Input, and Nudge Buttons (Done)

The Word Edit Dialog's three style/scope/component `ui.select` widgets,
its GT `ui.input`, and the eight bbox fine-tune nudge buttons now carry
stable `data-testid` props so Playwright tests and the
`pd-ocr-labeler-driver` agent can target them without falling back to
`get_by_label("GT" | "Component")` or `get_by_role("button", name="X+")`
patterns:

- Inputs / selects: `dialog-gt-input`, `dialog-style-select`,
  `dialog-scope-select`, `dialog-component-select`.
- Nudge buttons (Left/Right edge X-/X+, Top/Bottom edge Y-/Y+):
  `dialog-nudge-left-minus-button`, `dialog-nudge-left-plus-button`,
  `dialog-nudge-right-minus-button`, `dialog-nudge-right-plus-button`,
  `dialog-nudge-top-minus-button`, `dialog-nudge-top-plus-button`,
  `dialog-nudge-bottom-minus-button`, `dialog-nudge-bottom-plus-button`.

Existing browser tests in `tests/browser/test_word_edit_dialog.py`
migrated from accessible-label / role-by-text selectors to
`[data-testid="..."]` selectors for the GT input, the Component
select-as-dropdown opener, and all nudge clicks/visibility assertions.
Architecture doc `docs/architecture/ui-action-buttons.md` updated to
record the new testids in the Style/Component Controls and Fine-Tune
Nudge Buttons tables. The remaining dialog buttons (header
check/close, merge/split/delete, crop, refine, reset/apply nudges)
were already testid'd in earlier commits.

### Stable data-testid Backfill — Word Match Apply-Style/Component Selects (Done)

The Word Match scope-action toolbar grid (Page / Paragraph / Line /
Word rows) and the Apply-Style toolbar buttons were already fully
backfilled in earlier commits, with all corresponding browser tests
in `tests/browser/test_toolbar_*.py` and `tests/browser/test_word_match.py`
already on `[data-testid="..."]` selectors.

The two remaining `ui.select` widgets in the apply-style toolbar
(`apply_style_select` and `apply_component_select`) now also carry
`data-testid` props — `apply-style-select` and
`apply-component-select` — to round out the contract for that toolbar
section. The third select in the row (`apply_scope_select`) was
already testid'd as `scope-select`. Architecture doc
`docs/architecture/ui-action-buttons.md` section 7 now documents the
testid for every load-bearing dropdown / select in the labeler UI
(adding a `data-testid` column to the section-7 table). No browser /
unit tests changed: the existing tests do not yet open these selects,
and adding tests for select interaction is queued as a separate chunk
under "Word edit dialog operations" / "Toolbar scope actions
(line + word rows)" in the priority list.

### Stable data-testid Backfill — OCR Configuration Modal (Done)

`OCRConfigModal` now exposes `data-testid` props on every load-bearing
control so future Playwright tests and the `pd-ocr-labeler-driver`
agent can select by testid instead of relying on visible label copy
or fragile q-select wrappers:

- Header trigger: `ocr-config-trigger-button` (the `tune` icon).
- Dialog buttons: `ocr-rescan-models-button`, `ocr-config-cancel-button`,
  `ocr-config-apply-button`.
- Dialog inputs: `ocr-detection-model-select`,
  `ocr-recognition-model-select`, `ocr-hf-revision-input`.

No browser tests existed for this modal yet, so this commit is purely
a contract-establishing testid backfill — adding browser regression
coverage for the modal is queued as a follow-up. Architecture doc
`docs/architecture/ui-action-buttons.md` updated to record each new
testid alongside the label.

### Stable data-testid Backfill — Project Load Controls + Source Folder Dialog (Done)

`ProjectLoadControls` controls now carry `data-testid` props for stable
selection from Playwright tests and the `pd-ocr-labeler-driver` agent:

- Header row: `project-select`, `load-project-button`,
  `source-folder-button`.
- Source-folder dialog buttons: `source-folder-home-button`,
  `source-folder-up-button`, `source-folder-open-typed-button`,
  `source-folder-use-current-button`, `source-folder-cancel-button`,
  `source-folder-apply-button`.
- Source-folder dialog non-button elements: `source-folder-path-input`,
  `source-folder-current-path-label`.

Existing browser tests in `tests/browser/test_source_folder_dialog.py`,
`tests/browser/test_browser_smoke.py`, `tests/browser/test_home_page.py`,
`tests/browser/test_project_loading.py`, and `tests/browser/helpers.py`
migrated from accessible-name / role / fragile-CSS selectors to
`[data-testid="..."]` selectors. The OCR Configuration modal trigger
(`tune` icon) and its dialog body remain untestid'd and on the
backfill backlog.

Architecture doc `docs/architecture/ui-action-buttons.md` updated to
record each new testid alongside the label.

### Stable data-testid Backfill — Project Navigation Controls (Done)

`ProjectNavigationControls` buttons now carry `data-testid` props
(`nav-prev-button`, `nav-next-button`, `nav-goto-button`) for stable
selection from Playwright tests and the `pd-ocr-labeler-driver`
agent. All existing browser tests that selected these controls by
accessible name (`tests/browser/helpers.py`,
`tests/browser/test_navigation.py`,
`tests/browser/test_session_isolation.py`,
`tests/browser/test_project_loading.py`,
`tests/browser/test_home_page.py`) migrated to
`[data-testid="..."]` selectors. The page-number input and total
label still rely on accessible-label selection (`get_by_label("Page")`),
which is intentionally a more stable contract than button copy.
Architecture-doc button table in
`docs/architecture/ui-action-buttons.md` updated to record each new
testid alongside the label. Other load-bearing controls remain on
the testid backfill backlog for follow-up iterations.

### Stable data-testid Backfill — Page Actions (Done)

`PageActions` buttons now carry `data-testid` props for stable
selection from Playwright tests and the
`pd-ocr-labeler-driver` agent: `reload-ocr-button`,
`reload-ocr-edited-button`, `save-page-button`,
`save-project-button`, `load-page-button`, `rematch-gt-button`.
Browser tests in `tests/browser/test_page_actions.py` migrated from
accessible-name selectors to testid selectors. Architecture-doc
button table in `docs/architecture/ui-action-buttons.md` updated to
record each new testid alongside the label. Navigation controls
(`Prev` / `Next` / `Go To:`) and other load-bearing controls remain
on the testid backfill backlog for follow-up iterations.

### Session Restore (Done)

`SessionStateOperations` saves project path and page index on every
project load; at startup, when no CLI project is provided, the saved
session is restored via `_try_restore_session` in `app.py`.

### Multi-JSON Ground Truth Merge (Done)

`pages_manifest.json` support in `ProjectOperations.load_ground_truth_from_directory`.
Manifest lists source files with optional numeric page-key offsets (e.g. `{"file": "pages_r2.json", "offset": 100}`).
Fell back gracefully to `pages.json` when no manifest exists.

### Add-Word Workflow (Done)

`LineOperations.add_word_to_page` inserts a new `Word` with drawn bbox into the
nearest line. `PageState.add_word` exposes it through the state layer. Toolbar
"Add Word" button triggers image-tab draw mode; drawn rectangle is propagated
back via `ContentArea` callbacks to `WordMatchBbox.apply_add_word_bbox`.

### Save Project — Bulk Page Persist (Done)

Implemented `save_all_pages()` in `ProjectState` with `SaveProjectResult`
tracking. "Save Project" button wired in `PageActions` with notification
summary. Reuses existing `persist_page_to_file` infrastructure.

- Notification shows save summary (saved/skipped/failed counts).
- No regression in existing per-page Save Page behavior.
- At least one unit test validates the bulk save flow.

---

## Previously Completed Steps

- Per-Word Validation State with Line/Paragraph Rollup (Done)
- Preserve Per-Word GT Edits Across Save/Load (Done)
- Ground Truth PGDP Preprocessing (Done)
