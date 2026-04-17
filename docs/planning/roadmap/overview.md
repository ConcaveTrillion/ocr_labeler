# OCR Labeler Roadmap Overview

Development roadmap for OCR Labeler.

Status: implementation-aligned snapshot (updated 2026-04-16).

## Current Focus

- Editing-core wrap-up (remaining: add-word workflow, expand-bbox action)
- Remaining navigation ingestion gap (multi-JSON merge with page index offsets)
- Browser test coverage expansion (currently ~28% of 107 buttons; target 97%)
- Persistence metadata schema alignment and session restore

## Completed

- Foundational persistence, OCR save/load/reset, notifications
- BBox operations, line filtering, font injection
- Paragraph region selection + paragraph merge/delete/split workflows
- Word deletion workflow + edit-triggered overlay/cache refresh improvements
- Word merge-left/merge-right + split-word edit workflows
- Enhanced matching UI baseline (unmatched GT placeholders, mismatch overlays, monospace surfaces)
- Multi-page navigation controls + route/page index synchronization
- Backend project export formats (json/jsonl/csv)
- Word tag editing: style labels, scopes, word components via toolbar and dialog
- Unified footnote marker behavior and migration to pd-book-tools label model
- Ground truth PGDP preprocessing via `PGDPResults` at GT load time
- Preserve per-word GT edits across save/load + explicit "Rematch GT" action
- Per-word validation state with line/paragraph rollup and persistence
- Save Project — bulk page persist (all worked pages in one action)
- DocTR training/validation export dialog with scope and style-based filtering
- Rebox workflow, rebox auto-refine, selection refine actions
- Word edit dialog with interactive zoom slider
- Provenance tracking via `UserPageEnvelope` (schema v2.1)
- OS-aware persistence paths (XDG, macOS Library, Windows APPDATA)
- Local state cleanup utilities

## Next Milestones

- Navigation and multi-page support (remaining ingestion gap)
- Editing-core remainder (add-word, expand-bbox)
- Browser test coverage expansion (14-commit phased plan)
- Persistence metadata schema + session restore
- Performance and polish (derived cache, debounced updates)
- Distribution strategy

## Integrated Sequence

1. Close remaining navigation ingestion work
2. Remaining editing-core (add-word, expand-bbox)
3. Browser test coverage + save/load round-trip tests
4. Persistence metadata schema + session restore
5. Performance/polish + derived cache strategy
6. Distribution strategy

## References

- [Editing Core (In Progress)](editing-core.md)
- [Enhanced UI and Matching](enhanced-ui-matching.md)
- [Navigation and Multi-page](navigation-multi-page.md)
- [Performance and Polish](performance-polish.md)
- [Testing and Documentation](testing-documentation.md)
- [Training and Validation Export](training-validation-export.md)
- [Distribution Strategy](distribution-strategy.md)
- [Persistence Track (named milestones)](persistence-milestones.md)
