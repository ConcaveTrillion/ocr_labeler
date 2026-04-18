# Roadmap Phase 5: Navigation and Multi-Page Support

**Priority:** Medium
**Status:** In Progress

## Completed

- Multi-page navigation controls (Prev / Next / direct page number input)
- Route and page index synchronization
- Lazy per-page OCR loading with three-tier fallback (user-saved → cached → live OCR)
- Force-OCR override tracking per page index
- Project discovery and listing via `ProjectDiscoveryOperations`
- ~~Merge multiple JSON project files with page index offsets~~ (Done — `pages_manifest.json` support
  in `ProjectOperations.load_ground_truth_from_directory`; manifest lists source files with optional
  numeric page-key offsets)

## Remaining

No remaining items at this time.
