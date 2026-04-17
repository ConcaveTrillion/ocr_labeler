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
