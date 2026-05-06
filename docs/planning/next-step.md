# Next Step: Browser Test Coverage Expansion

**Status:** Not Started

Goal: expand browser test coverage from 28% to 97% of 107 UI buttons
using the 14-commit phased plan in
[browser-ui-test-plan.md](browser-ui-test-plan.md).

## Priority Order

1. Toolbar scope actions (line + word rows) — 0% currently
2. Word edit dialog operations (merge/split/crop/refine/nudge) — 0%
3. Per-line action buttons (GT→OCR, Validate, Delete) — 0%
4. Source folder dialog — 0%
5. Header/load controls — 11%
6. Keyboard shortcuts — 0%
7. Image tab controls — 0%

## Done Criteria

- All 14 commits from the browser test plan are implemented.
- `make test-browser` passes reliably with `pytest -n auto`.

---

## Previously Completed Next Steps

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
