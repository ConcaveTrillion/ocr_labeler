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

## Planned Sequence

- ~~**Metadata + Session Baseline:**~~ (Deferred — user metadata schema design
  exists but not yet prioritized; validation persistence landed via
  word_attributes sidecar)
- **Save Project (bulk page persist) — Next:** extend per-page "Save Page" to a
  "Save Project" action that persists all worked pages in a single
  operation. Should use cached in-memory page versions where available,
  fall back to already-persisted cache files for untouched pages, and
  skip pages that have never been loaded. Wire a UI action (toolbar or
  menu) and surface progress/result via notification.
- **Disconnect/Prewarm Reliability:** disconnect flush + optional cache prewarm
- **Derived Cache Optimization (later):** derived word/line cache strategy and performance-focused persistence

## Source Planning Docs

- [Persistence & Session Cache Plan](../persistence-session-cache-plan.md)
- [Word/Line Derived Cache Planning](../persistence-word-line-derived-cache.md)
- [User Persistence Metadata Schema Plan](../user-persistence-metadata-schema.md)
