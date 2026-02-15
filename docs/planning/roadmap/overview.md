# OCR Labeler Roadmap Overview

Development roadmap for OCR Labeler.

Status: planning snapshot.

## Current Focus

- Editing core (word and line-level)
- Page cache reliability and compatibility checks
- User metadata + session snapshot persistence baseline

## Completed

- Foundational persistence, OCR save/load/reset, notifications
- BBox operations, line filtering, font injection

## Next Milestones

- Enhanced UI and matching (after metadata persistence baseline is in place)
- Navigation and multi-page support (includes disconnect/session flush integration)
- Performance and polish (includes derived cache and performance-focused persistence)
- Testing and documentation
- Training and validation export
- Distribution strategy

## Integrated Sequence

- Editing core + page cache reliability
- User metadata persistence gate before broader feature additions
- Enhanced UI and matching on top of metadata-aware persistence
- Navigation/multi-page + reliable disconnect/session flush behavior
- Performance/polish + deferred derived cache strategy
- Testing/docs, export workflows, and distribution strategy

## References

- [Editing Core (In Progress)](editing-core.md)
- [Enhanced UI and Matching](enhanced-ui-matching.md)
- [Navigation and Multi-page](navigation-multi-page.md)
- [Performance and Polish](performance-polish.md)
- [Testing and Documentation](testing-documentation.md)
- [Training and Validation Export](training-validation-export.md)
- [Distribution Strategy](distribution-strategy.md)
- [Persistence Track (named milestones)](persistence-milestones.md)
