# Roadmap Phase 8: Training and Validation Export

**Priority:** Medium
**Status:** Mostly Complete

## Completed

- DocTR export backend: `DocTRExportOperations` with detection + recognition
  dataset generation, GT-first resolution, validation gating, and word
  filtering by text style label or word component.
- Export dialog UI: `ExportDialog` with scope selection (current page vs all
  validated pages) and multi-select style-based filtering.
- Export CLI: `ocr_labeler/operations/export/cli.py` for headless export.
- `ProjectState` export status tracking (NOT_EXPORTED / EXPORTED / STALE)
  with staleness detection after page edits.

## Remaining

- Classification dataset export (labels with GT text + style/component flags)
  — backend exists but not wired in the UI dialog.
- Batch export progress indicator for large projects.
