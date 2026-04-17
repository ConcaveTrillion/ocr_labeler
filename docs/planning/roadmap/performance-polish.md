# Roadmap Phase 6: Performance and Polish

**Priority:** Low
**Status:** Planned

## Already In Place

- Page load timing instrumentation (`page_timing_logger`)
- ThreadPoolExecutor-based image encoding with LRU eviction
- Text caching with page index validation
- Local state cleanup utilities (log/cache removal)

## Scope (Remaining)

- Optional debounced updates for frequent GT edits
- Graceful fallbacks when optional dependencies are unavailable
- Derived word/line cache strategy (see
  [persistence-word-line-derived-cache.md](../persistence-word-line-derived-cache.md))
- Disconnect flush + optional cache prewarm
