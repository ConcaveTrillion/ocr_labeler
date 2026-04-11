# Next Step: Save Project — Bulk Page Persist

Goal: let users save all worked pages in a single action instead of
saving each page individually.

## Problem

Users can only save one page at a time via the "Save Page" button.
After editing multiple pages across a labeling session, there is no way
to persist all changes at once.  This is tedious and error-prone — users
may forget to save some pages, losing work if the session ends.

## Desired Behavior

- A "Save Project" button in the page actions bar persists all pages
  that have been loaded and worked on in the current session.
- Uses cached in-memory page versions where available.
- Skips pages that have never been loaded (no `PageState` exists).
- Surfaces progress and result via notification (e.g. "Saved 5/8 pages").
- Does not re-run OCR or modify page source for pages that are already
  in "filesystem" (user-saved) state unless they have been further
  edited (auto-cached since last save).
- Saves all pages to the same labeled-projects directory used by
  "Save Page".

## Implementation Sketch

### State Layer (`ProjectState`)

1. Add `save_all_pages() -> SaveProjectResult` method that:
   - Iterates `self.page_states` (pages that have been accessed).
   - For each page with a loaded `PageState`, calls
     `page_state.persist_page_to_file(page_index)`.
   - Tracks success/failure counts.
   - Returns a result object with counts.

2. Add `SaveProjectResult` dataclass:
   - `saved_count: int`
   - `skipped_count: int`
   - `failed_count: int`
   - `total_count: int`

### ViewModel Layer

1. Wire `save_all_pages` through `ProjectStateViewModel` as an async
   command, similar to existing `command_save_page`.

### UI Layer (`PageActions`)

1. Add "Save Project" button next to existing "Save Page" button.
2. Disable when no project is loaded.
3. On click, call the save-all command and show a notification with
   the result summary.

### Persistence

No new persistence format needed — reuses existing `persist_page_to_file`
and `PageOperations.save_page()` infrastructure.

## Edge Cases

- Page that was never navigated to has no `PageState` — skip it.
- Page load failed (page is None in project) — skip with warning.
- Concurrent save while navigating — the save iterates a snapshot of
  page indices; navigation during save is safe because each page's
  `persist_page_to_file` is self-contained.
- All pages already saved — notification says "All pages already saved"
  or "Saved 0 pages (8 already up to date)".

## Tests

- Unit: `save_all_pages` with no loaded pages returns zero counts.
- Unit: `save_all_pages` with multiple loaded pages saves all of them.
- Unit: `save_all_pages` skips pages with no `PageState`.
- Unit: failed page save increments `failed_count` without aborting.
- Round-trip: save project, reload pages, verify content preserved.

## Done Criteria

- Users can save all worked pages with a single button click.
- Notification shows save summary (saved/skipped/failed counts).
- No regression in existing per-page Save Page behavior.
- At least one unit test validates the bulk save flow.

---

## Previously Completed Steps

- Per-Word Validation State with Line/Paragraph Rollup (Done)
- Preserve Per-Word GT Edits Across Save/Load (Done)
- Ground Truth PGDP Preprocessing (Done)
