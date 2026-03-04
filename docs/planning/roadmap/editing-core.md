# Roadmap Phase 3: Word and Line-Level Editing Core

**Priority:** High
**Status:** In Progress

## Recently Completed

- Paragraph block grouping from image region selection (two-way image/panel sync)
- Paragraph actions: merge, delete, split-after-line, split-by-selected-lines
- Word action: delete selected words
- Post-edit state refresh: overlay refresh + text cache invalidation + GT re-match hooks
- Word actions: merge-left, merge-right
- Split-word UI and bbox-aware split workflow
- Word/line visual crop previews in the editor surface
- GT rematch + overlay/cache refresh after structural edits

## Block/Line Editing

- Additional line/paragraph refinement workflows

## Word Editing Infrastructure

### Editing State

- Persist/restore validation-focused per-line editing state where missing

### BBox Editing

- Add-word workflow: draw a bbox on the image to insert a new word (default target: nearest line/paragraph)
- Rebox workflow: redraw an existing word bbox from the UI (replace current bbox with drawn bbox)
- Refine-bbox action for selected word(s)
- Expand-bbox action for selected word(s)

## Image Interaction

- Zoom controls for image inspection/editing (zoom in, zoom out, reset)

## Ground Truth and State

- Persist and restore line validation + word GT fields
