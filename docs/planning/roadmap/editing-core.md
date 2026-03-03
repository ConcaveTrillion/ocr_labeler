# Roadmap Phase 3: Word and Line-Level Editing Core

**Priority:** High
**Status:** In Progress

## Recently Completed

- Paragraph block grouping from image region selection (two-way image/panel sync)
- Paragraph actions: merge, delete, split-after-line, split-by-selected-lines
- Word action: delete selected words
- Post-edit state refresh: overlay refresh + text cache invalidation + GT re-match hooks

## Active Next Item (Started)

- Word actions: merge-left, merge-right

## Block/Line Editing

- Additional line/paragraph refinement workflows

## Word Editing Infrastructure

- Word view-model abstraction strategy
- Per-line advanced editor (thumbnails, OCR/GT controls, validation actions)
- Word actions: merge-left, merge-right
- Split-word UI and edit-bbox workflow
- Quick crop actions and post-edit overlay refresh

## Ground Truth and State

- Recompute fuzz scores after GT edits
- Invalidate per-page image cache after edits
- Persist and restore line validation + word GT fields
