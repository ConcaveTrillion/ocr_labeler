# OCR Labeler Roadmap Overview

Development roadmap for OCR Labeler.

Status: forward roadmap snapshot (updated 2026-04-22).

## Current Focus

- Save/load browser round-trip regression coverage
- Export UX completion (classification mode + long-running batch progress)
- Persistence reliability hardening (disconnect flush + prewarm)

## Active Milestones

- Browser save/load round-trip tests (UI-level persistence verification)
- Export dialog support for classification dataset mode
- Batch export progress indicator for large projects
- Disconnect flush + optional cache prewarm
- Derived word/line cache strategy and debounced GT updates
- Distribution strategy and packaging variants
- **Mac / Apple Silicon (MPS) support** — test and validate OCR inference on Apple Silicon via PyTorch MPS backend;
  ensure device selection (CUDA > MPS > CPU) works correctly in the labeler's OCR page operations

## Integrated Sequence

1. Testing hardening: browser save/load round-trip tests
2. Export UX completion: classification mode + batch progress
3. Persistence reliability: disconnect flush + cache prewarm
4. Performance/polish: derived cache + debounced GT updates
5. Distribution strategy

## References

- [Performance and Polish](performance-polish.md)
- [Testing and Documentation](testing-documentation.md)
- [Training and Validation Export](training-validation-export.md)
- [Distribution Strategy](distribution-strategy.md)
- [Persistence Track (named milestones)](persistence-milestones.md)
