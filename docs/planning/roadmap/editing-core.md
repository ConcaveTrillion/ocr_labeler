# Roadmap Phase 3: Word and Line-Level Editing Core

**Priority:** High
**Status:** In Progress

## Block/Line Editing

- Paragraph block grouping from image region selection
- Merge lines workflow with checkbox selection and accept action
- Delete line workflow, including structural updates and refresh behavior

## Word Editing Infrastructure

- Word view-model abstraction strategy
- Per-line advanced editor (thumbnails, OCR/GT controls, validation actions)
- Word actions: delete, merge-left, merge-right
- Split-word UI and edit-bbox workflow
- Quick crop actions and post-edit overlay refresh

## Ground Truth and State

- Recompute fuzz scores after GT edits
- Invalidate per-page image cache after edits
- Persist and restore line validation + word GT fields
