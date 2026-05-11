# OCR Labeler Roadmap Overview

Development roadmap for OCR Labeler.

Status: forward roadmap snapshot (updated 2026-04-22).

## Current Focus

- Save/load browser round-trip regression coverage
- Export UX completion (classification mode + long-running batch progress)
- Persistence reliability hardening (disconnect flush + prewarm)

## Active Milestones

- Browser save/load round-trip tests (UI-level persistence verification)
- Export dialog support for classification dataset mode
- Batch export progress indicator for large projects
- Disconnect flush + optional cache prewarm
- Derived word/line cache strategy and debounced GT updates
- Distribution strategy and packaging variants
- **Dev-local-aware `upgrade-deps`** — refuse-with-message when the venv
  has editable sibling pd-* checkouts (detected via `uv pip show
  pd-book-tools`, `.venv/.pd-dev-local` marker, or `PD_DEV_LOCAL=1`),
  add `upgrade-deps-local` sibling that re-applies editable installs
  after `uv sync`. Workspace-wide standard, spec at
  [`docs/dev-local-upgrade-flow.md`](../../dev-local-upgrade-flow.md).
  Applicable but deferred — legacy NiceGUI labeler is being phased out
  in favor of `pd-ocr-labeler-spa`; land the fix when the workspace
  rollout reaches this repo, not blocked on SPA cutover since the legacy
  labeler still receives dep updates during migration.
- **Mac / Apple Silicon (MPS) support** — test and validate OCR inference on Apple Silicon via PyTorch MPS backend;
  ensure device selection (CUDA > MPS > CPU) works correctly in the labeler's OCR page operations
- **Local-mode port auto-select fallback + stable bookmarks + in-UI URL
  display** — converging shared dev-UX behavior across all local pd-*
  web apps (sibling items: `pd-prep-for-pgdp` commit `b23b913`,
  `pd-ocr-labeler-spa` commit `b956275`). Triggered by a real
  stale-port collision (21h-old orphan blocking startup). Proposed
  behavior, **local mode only**:
  1. **Auto-select fallback.** Try persisted-last-port first, then
     default port, then `port=0` (kernel picks a free port). If user
     passes `--port N` explicitly, fail loud on collision (no fallback).
  2. **Stable bookmarks.** Persist the last successfully-bound port in
     a small state file so the user's browser bookmark survives across
     restarts in the common case.
  3. **URL visible in the running UI.** Local-mode users may close the
     console window. The NiceGUI UI itself must surface the current URL
     somewhere persistent (footer, header, "About" panel, or
     copy-to-clipboard widget). Belt-and-suspenders: console print +
     in-UI display.

  Acceptance:
  - Tests: default-port-free; default-port-taken-fallback-succeeds;
    explicit-port-collision-fails-loud;
    persisted-port-reused-on-next-start;
    persisted-port-taken-falls-through.
  - In-UI URL-visible assertion (browser/Playwright).
- **Glyph-level annotations (passthrough only)** — preserve `Word.glyph_annotations`
  (ligatures, long-s positions, swash flag) through save/load without dropping or mutating.
  Scope is intentionally minimal: **no UI**, no editing affordances. Rationale: the rich
  editing UI for glyph annotations belongs to `pd-ocr-labeler-spa` (the FastAPI+React
  replacement). The legacy NiceGUI labeler must not erase annotations written by the SPA
  or by an automated driver. Data model authored in `pd-book-tools`; cross-reference its
  spec when implementing serializer round-trip + a regression test that opens, edits an
  unrelated word, saves, and asserts annotations on other words are byte-identical.

## Integrated Sequence

1. Testing hardening: browser save/load round-trip tests
2. Export UX completion: classification mode + batch progress
3. Persistence reliability: disconnect flush + cache prewarm
4. Performance/polish: derived cache + debounced GT updates
5. Distribution strategy

## References

- [Performance and Polish](performance-polish.md)
- [Testing and Documentation](testing-documentation.md)
- [Training and Validation Export](training-validation-export.md)
- [Distribution Strategy](distribution-strategy.md)
- [Persistence Track (named milestones)](persistence-milestones.md)
