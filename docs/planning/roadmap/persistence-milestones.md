# Roadmap Track: Persistence and Cache Reliability

**Priority:** High
**Status:** In Progress

This track captures persistence work that cuts across product roadmap milestones.

## Roadmap Placement

- **Page Cache Baseline** aligns with editing-core work.
- **Metadata + Session Baseline** is a pre-enhanced-UI gate so user
  metadata persistence is stable before broader feature additions.
- **Disconnect/Prewarm Reliability** aligns with navigation/multi-page reliability work.
- **Derived Cache Optimization** is intentionally deferred to
  performance/polish work after core behavior and metadata schema are
  stable.

## Completed

- ~~**Page Cache Baseline:**~~ Per-page save/load with provenance tracking via
  `UserPageEnvelope` (schema v2.1). Includes `word_attributes` sidecar for
  validation state and GT edits.
- ~~**Save Project (bulk page persist):**~~ `save_all_pages()` in
  `ProjectState` persists all worked pages in a single operation with
  progress/result notification via `SaveProjectResult`.
- ~~**Metadata + Session Baseline (Phase B — Session Restore):**~~ `SessionState`
  dataclass + `SessionStateOperations` for save/load/clear; saved on every
  successful project load; restored at startup when no CLI project or URL
  is provided (`app.py` `_try_restore_session`).

## Planned Sequence

- **Metadata + Session Baseline (Phase A):** user metadata schema design exists but
  not yet prioritized.
- **Disconnect/Prewarm Reliability:** disconnect flush + optional cache prewarm
- **Derived Cache Optimization (later):** derived word/line cache strategy and performance-focused persistence

## Source Planning Docs

- [Persistence & Session Cache Plan](../persistence-session-cache-plan.md)
- [Word/Line Derived Cache Planning](../persistence-word-line-derived-cache.md)
- [User Persistence Metadata Schema Plan](../user-persistence-metadata-schema.md)
