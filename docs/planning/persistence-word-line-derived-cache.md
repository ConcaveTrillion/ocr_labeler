# Phase D Plan: Word/Line Derived Cache

## Context

This phase extends the existing persistence plan after the page-level OCR/image/session cache lanes are stable.

Current persistence focus (MVP to Phase C) is page-level cache correctness, lane separation, and session restore.
This document proposes a **later phase** for caching derived artifacts used by word/line-centric UI views.

Related prerequisite: [Persistence & Session Cache Plan](persistence-session-cache-plan.md)

## Problem

Even with page-level OCR cache hits, derived word/line view artifacts may still be recomputed repeatedly:

- line structure projections/groupings used by comparison/editing views
- cropped word/line image snippets generated for visual inspection

Repeated derivation can increase latency when revisiting pages, especially during interactive editing workflows.

## Goals

- Reduce repeated compute for derived line/word artifacts.
- Keep invalidation safety equivalent to page-level cache guarantees.
- Avoid excessive file count and disk churn from tiny per-word assets.
- Preserve lane semantics: derived cache is optimization-only and non-authoritative.

## Non-Goals

- Replacing canonical `Save Page` user outputs.
- Storing every transient UI artifact indefinitely.
- Introducing a database dependency.

## Recommended Scope Split

### D1: Persist line structures (recommended)

Persist line structure artifacts that are expensive to re-derive and broadly reusable across UI features.

Examples:

- line-to-word membership maps
- normalized ordering/grouping metadata
- lightweight per-line view-model-ready descriptors

Rationale: high reuse and comparatively compact metadata footprint.

### D2: Word/line image crops (optional, measured)

Default approach: in-memory LRU cache only.

Optional disk persistence can be added later if profiling confirms crop generation/encoding is a bottleneck.

Rationale: persistent tiny-file caches can increase I/O overhead and invalidation complexity.

## Cache Model

## Artifact lane

- New optimization-only lane under `local-data/labeled-ocr/cache-derived/`
- Never overwrites canonical labeled outputs.

## Keying and compatibility

Derived cache keys should include at minimum:

- page cache compatibility fingerprint (source image + OCR engine/version + `pd-book-tools` version fingerprint)
- derived algorithm version (explicit constant, bumped on logic changes)
- render/transform parameters (for image crops only)

If any component changes, treat cached artifact as stale and regenerate.

## File layout (proposed)

- `cache-derived/<project>/<page>/line_structure.v{n}.json`
- `cache-derived/<project>/<page>/manifest.json`
- Optional crop pack (if enabled later):
  - `cache-derived/<project>/<page>/crop_pack.v{n}.bin` (or equivalent packed format)
  - Avoid one-file-per-word layout.

## Invalidation Rules

Derived artifacts are valid only if:

- parent page cache compatibility passes
- derived algorithm version matches
- requested render parameters match (crop artifacts)

On mismatch:

- ignore stale derived entry
- regenerate on demand
- best-effort replace derived cache atomically

## Runtime Strategy

### Read path

1. Attempt in-memory cache hit.
2. Attempt disk-derived cache hit (if enabled for artifact type).
3. Regenerate from page OCR data and return.
4. Persist regenerated artifact asynchronously (best effort).

### Write path

- Debounced/bounded writes to avoid disk thrash during rapid navigation.
- Atomic file replace for manifest and structured JSON payloads.

## UX/Behavior

- No new required user steps.
- No new source badge type required for MVP of this phase (still page-origin driven: `RAW OCR` / `CACHED OCR` / `LABELED`).
- Optional debug/diagnostic metrics may report derived cache hit rate.

## Acceptance Criteria

- Revisiting a page with unchanged compatibility fingerprint avoids recomputing line structures.
- Derived cache invalidates correctly on algorithm version bump.
- Derived cache invalidates correctly when parent page compatibility fails.
- Disk cache, if enabled for crops, does not create unbounded small-file growth.
- Failures in derived cache read/write never block navigation or editing.

## Testing Plan

- Unit tests for derived cache key composition and invalidation.
- Unit tests for algorithm-version invalidation behavior.
- Unit tests for stale-parent-fingerprint invalidation behavior.
- Integration-style test for regenerate-and-persist flow with best-effort write failures.
- If crop persistence is enabled: tests for pack read/write and bounded eviction.

## Risks

- Over-caching low-value artifacts can increase complexity.
- Large crop packs may increase memory pressure during pack operations.
- Version drift if algorithm version constants are not maintained.

Mitigations:

- Start with line structures only.
- Add crop persistence only with profiling evidence.
- Keep explicit `DERIVED_CACHE_VERSION` constants and test coverage.

## Open Questions

- Should derived cache be globally size-bounded per project directory?
- Is a lightweight binary pack needed initially, or can JSON + compressed payload suffice?
- Should line structure cache be eager (on page load) or lazy (on first line-view access)?
- Which tooling should back the derived cache: `diskcache` alone, or a two-tier approach with `cachetools` (memory LRU) + `diskcache` (persistent on-disk cache)?

## Execution Checklist

- [ ] Add derived cache models and manifest helpers.
- [ ] Add line structure cache read/write integration.
- [ ] Add algorithm version keying and invalidation checks.
- [ ] Add in-memory LRU layer for crop artifacts.
- [ ] Add optional disk crop-pack prototype behind feature flag.
- [ ] Add tests for derived cache hit/miss + invalidation.
- [ ] Add docs updates for cache behavior and disk usage limits.
