# Persistence & Session Cache Plan

## Problem

Session reloads currently lose in-memory loaded pages, so users can re-trigger OCR for pages that were already processed in prior sessions.

The app can load saved page JSON from disk, but persistence is mostly user-driven (manual save actions), and there is no formal session restore plan.

## Goals

- Make OCR a one-time cost per unchanged source image in typical workflows.
- Restore useful session context after reload (project + page position) without surprising users.
- Keep behavior safe when source images change (no stale cache usage).
- Ensure cache invalidation also occurs when OCR/parsing semantics change, including OCR engine changes and `pd-book-tools` version changes (post-processing differences).
- Preserve existing UX: no new required steps for users.
- Keep **auto cache persistence** separate from **user-authoritative Save Page edits**.
- Improve source/status visibility so users can distinguish raw, cached, and labeled page origins.

## Non-Goals

- Full multi-user synchronization across machines.
- Introducing a database service.
- Redesigning navigation or page controls.
- Reinterpreting auto cache writes as user-approved labeling edits.

## Persistence Lanes (Explicit Separation)

### Lane A: Auto Cache (performance path)

- Purpose: avoid re-running OCR for unchanged inputs and unchanged OCR/post-processing stack.
- Trigger: automatic, after successful OCR load.
- Data: OCR-derived page snapshot + manifest metadata for compatibility checks.
- Authority: non-authoritative optimization artifact; can be invalidated/rebuilt anytime.
- UI state label: `CACHED OCR`.

### Lane B: Save Page (user edits path)

- Purpose: persist user changes to OCR/Ground Truth/annotation data as intentional edits.
- Trigger: explicit user action (`Save Page`) only.
- Data: user-modified page content intended as canonical labeled output.
- Authority: authoritative user work product; must not be silently overwritten by auto cache logic.
- UI state label: `LABELED`.

### Lane C: Unsaved OCR (in-memory/raw lane)

- Purpose: represent OCR output that has not yet been persisted to cache or labeled output.
- Trigger: fresh OCR run before cache save completes (or when cache disabled/missed).
- UI state label: `RAW OCR`.

## Current State Summary

- `ProjectState.ensure_page()` first attempts to load from `local-data/labeled-ocr`, then falls back to OCR.
- `PageOperations.save_page()/load_page()` persist per-page JSON/image artifacts.
- Save/load is exposed in UI controls, but not consistently auto-triggered.
- Generic state persistence helpers exist but are not integrated into app/project session restore flow.

## Proposed Design

### 1) Auto-persist OCR outputs

When OCR succeeds for a page loaded through `ensure_page`, persist that page automatically in the background.

Outcome: first OCR pass produces reusable artifacts without relying on manual “Save Page”.

Important: this lane must write to cache-only artifacts and never replace or downgrade user-authored Save Page outputs.

### 2) Add cache manifest with freshness checks

Store per-project cache metadata (e.g., `local-data/labeled-ocr/<project>_manifest.json`) including:

- page index / page number
- source image path (relative if possible)
- source image fingerprint (`mtime_ns`, `size`, optional checksum)
- saved artifact filenames
- OCR engine/source metadata (best-effort)
- OCR engine identity + version (or equivalent config fingerprint)
- `pd-book-tools` version (or post-processing fingerprint)
- saved timestamp

Before using saved page JSON, verify fingerprint compatibility with current source image.
Before using saved page JSON, verify compatibility across:

- source image fingerprint
- OCR engine identity/version
- `pd-book-tools` version/post-processing fingerprint

Expose cache metadata in UI tooltip when page source is `CACHED OCR` (and optionally `LABELED`), including:

- OCR engine identity/version
- `pd-book-tools` version/fingerprint
- cache saved timestamp

Outcome: avoid stale cached OCR when source images are modified/replaced.

### 3) Persist and restore session snapshot

Persist lightweight app/session state (e.g., `local-data/labeled-ocr/session_state.json`):

- last loaded project key/path
- last page index
- selected project key
- optional recent project list

Restore this state on session start when valid, then deep-link routing can still override page/project when present.

Outcome: reload returns users to prior context with minimal friction.

### 4) Save-on-disconnect (best effort)

On NiceGUI disconnect, attempt to flush current dirty/loaded page state before detaching listeners.

Outcome: maximize retained work on tab refresh/close.

## Implementation Phases

## Phase A (MVP)

- Auto-save OCR result after successful OCR page load.
- Add manifest write/update hooks.
- Validate cache freshness before `load_page` acceptance.
- Extend page source status model to include `CACHED OCR` alongside `RAW OCR` and `LABELED`.
- Add tooltip surface for version/fingerprint metadata.

Acceptance:

- Reloading a previously OCR’d unchanged page does not call OCR again.
- Modified source image invalidates stale cache and re-runs OCR.
- OCR engine/version change invalidates stale cache and re-runs OCR.
- `pd-book-tools` version/post-processing change invalidates stale cache and re-runs OCR.
- Source badge shows `CACHED OCR` when page loaded from compatible cache.
- Source badge shows `RAW OCR` for unsaved OCR output.
- Source badge shows `LABELED` for explicit user-saved labeled output.
- Tooltip for cached/labeled entries includes engine + version/fingerprint metadata.

## Phase B

- Add app/session snapshot read/write.
- Restore last project/page on startup when not overridden by URL.

Acceptance:

- Browser reload restores last project and page index.
- Invalid/missing project snapshot fails gracefully (no crash; fallback to chooser).

## Phase C

- Add best-effort disconnect flush.
- Add optional bounded prewarm of nearby pages from disk cache.

Acceptance:

- Refresh shortly after navigating/saving retains latest page state in most cases.

## Data & File Layout

Suggested artifacts under `local-data/labeled-ocr/`:

- **User edits lane (existing canonical outputs):** `<project>_<page>.json`, `<project>_<page>.png|jpg` (from explicit `Save Page`)
- **Auto cache lane (new):** separate cache namespace/path (example: `cache/<project>_<page>.json`, `cache/<project>_<page>.png|jpg`)
- New per-project cache manifest: `<project>_manifest.json` (or `cache/<project>_manifest.json` if colocated with cache lane)
- New session snapshot: `session_state.json`

Note: final directory naming can vary, but lane separation is required to prevent ambiguity.

## Safety & Compatibility

- Keep all features backward compatible with existing saved page files.
- Treat manifest/session files as optional (if missing/corrupt, fallback to existing behavior).
- Keep persistence writes best-effort; never block UI navigation on disk failures.
- Enforce one-way protection: auto cache writes must not overwrite explicit `Save Page` user edits.

## Testing Plan

- Unit tests for manifest fingerprint validation logic.
- Unit tests for cache hit/miss decision path.
- Unit tests for session snapshot parse/validation.
- Unit tests for source label mapping (`RAW OCR` vs `CACHED OCR` vs `LABELED`).
- Integration-style test (state layer) for:
  - first load OCR + auto-save
  - second load from cache (no OCR)
  - cache invalidation after source image metadata change
  - cache invalidation after OCR engine/version change
  - cache invalidation after `pd-book-tools` version/post-processing change
  - UI/viewmodel source text + tooltip metadata propagation for each source lane

## Risks

- Excessive disk writes if auto-save triggers too often.
- Race conditions between navigation/loading and background save tasks.
- Cross-platform path normalization edge cases.

Mitigations:

- Debounce or skip writes when no page changes detected.
- Use atomic write pattern for manifest/session files.
- Store normalized relative paths + defensive path resolution.

## Open Questions

- Should checksums be mandatory or metadata-only (`mtime_ns` + `size`) for MVP?
- Should session restore be per-browser-session only or global last-state?
- Do we need a user toggle to disable auto-persist for experimentation workflows?
- Should `Load Page` prefer user-edit lane first, then cache lane fallback, then OCR?
- For persistence implementation, should we evaluate a two-tier strategy using `cachetools` (in-memory LRU) with `diskcache` (on-disk reloadable cache)?

## Execution Checklist

- [ ] Add manifest model + read/write helpers in persistence operations.
- [ ] Define separate storage namespace/path for auto cache vs `Save Page` outputs.
- [ ] Wire auto-save after OCR success into auto-cache lane only.
- [ ] Add cache freshness validation in page load path.
- [ ] Include OCR engine/version + `pd-book-tools` version in cache compatibility checks.
- [ ] Extend page source model to represent `raw_ocr`, `cached_ocr`, and `labeled` distinctly.
- [ ] Add tooltip metadata plumbing (engine/version/fingerprint/timestamp) for cached/labeled statuses.
- [ ] Ensure `Save Page` path persists user changes as authoritative output.
- [ ] Ensure auto cache path cannot overwrite authoritative `Save Page` output.
- [ ] Add session snapshot read/write + startup restore.
- [ ] Add best-effort disconnect flush.
- [ ] Add/extend tests for cache + restore behavior.
- [ ] Update README usage notes for persistence behavior.
