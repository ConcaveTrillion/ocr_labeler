# Roadmap Track: Persistence and Cache Reliability

**Priority:** High
**Status:** In Progress

This track captures persistence work that cuts across product roadmap milestones.

## Roadmap Placement

- **Page Cache Baseline** aligns with editing-core work.
- **Metadata + Session Baseline** is a pre-enhanced-UI gate so user metadata persistence is stable before broader feature additions.
- **Disconnect/Prewarm Reliability** aligns with navigation/multi-page reliability work.
- **Derived Cache Optimization** is intentionally deferred to performance/polish work after core behavior and metadata schema are stable.

## Planned Sequence

- **Page Cache Baseline (MVP):** page-level auto-cache lane + compatibility checks
- **Metadata + Session Baseline:** user metadata + session snapshot save/restore
- **Disconnect/Prewarm Reliability:** disconnect flush + optional cache prewarm
- **Derived Cache Optimization (later):** derived word/line cache strategy and performance-focused persistence

## Source Planning Docs

- [Persistence & Session Cache Plan](../persistence-session-cache-plan.md)
- [Word/Line Derived Cache Planning](../persistence-word-line-derived-cache.md)
- [User Persistence Metadata Schema Plan](../user-persistence-metadata-schema.md)
