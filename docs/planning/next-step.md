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
