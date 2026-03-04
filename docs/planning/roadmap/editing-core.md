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
- Per-word GT inline editing with simple single-line text input
- Per-word GT input UX polish: dynamic width near word length with live resize while typing
- Per-word GT commit behavior: persist on blur and Enter
- Per-word GT keyboard navigation: Tab to next word, Shift+Tab to previous word

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
