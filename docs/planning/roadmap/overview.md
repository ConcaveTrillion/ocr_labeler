# OCR Labeler Roadmap Overview

Development roadmap for OCR Labeler.

Status: implementation-aligned snapshot.

## Current Focus

- **Next:** Save Project — bulk page persist ([next-step.md](../next-step.md))
- Editing-core wrap-up (remaining bbox/line refinement)
- Remaining navigation ingestion gap (multi-JSON merge with page index offsets)
- Testing/documentation follow-through
- Export UX wiring for training/validation workflows

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

## Next Milestones

- Save Project (bulk page persist)
- Navigation and multi-page support (remaining ingestion gap)
- Performance and polish (includes derived cache and performance-focused persistence)
- Testing and documentation
- Training and validation export
- Distribution strategy

## Integrated Sequence

- Save Project (bulk page persist)
- Close remaining navigation ingestion work
- Performance/polish + deferred derived cache strategy
- Testing/docs + export UI integration
- Distribution strategy

## References

- [Editing Core (In Progress)](editing-core.md)
- [Enhanced UI and Matching](enhanced-ui-matching.md)
- [Navigation and Multi-page](navigation-multi-page.md)
- [Performance and Polish](performance-polish.md)
- [Testing and Documentation](testing-documentation.md)
- [Training and Validation Export](training-validation-export.md)
- [Distribution Strategy](distribution-strategy.md)
- [Persistence Track (named milestones)](persistence-milestones.md)
