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
- **Glyph-level annotations (passthrough only)** — preserve `Word.glyph_annotations`
  (ligatures, long-s positions, swash flag) through save/load without dropping or mutating.
  Scope is intentionally minimal: **no UI**, no editing affordances. Rationale: the rich
  editing UI for glyph annotations belongs to `pd-ocr-labeler-spa` (the FastAPI+React
  replacement). The legacy NiceGUI labeler must not erase annotations written by the SPA
  or by an automated driver. Data model authored in `pd-book-tools`; cross-reference its
  spec when implementing serializer round-trip + a regression test that opens, edits an
  unrelated word, saves, and asserts annotations on other words are byte-identical.

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
