# Roadmap Phase 3: Word and Line-Level Editing Core

**Priority:** High
**Status:** Mostly Complete

## Recently Completed

- Paragraph block grouping from image region selection (two-way image/panel sync)
- Paragraph actions: merge, delete, split-after-line, split-by-selected-lines
- Word action: delete selected words
- Post-edit state refresh: overlay refresh + text cache invalidation + GT re-match hooks
- Word actions: merge-left, merge-right
- Split-word UI and bbox-aware split workflow
- Rebox workflow: redraw an existing word bbox from the UI and replace it
- Rebox auto-refine: newly redrawn word bboxes are refined immediately
- Selection refine actions for word/line/paragraph scopes in the word editor
- Word/line visual crop previews in the editor surface
- GT rematch + overlay/cache refresh after structural edits
- Per-word GT inline editing with simple single-line text input
- Per-word GT input UX polish: dynamic width near word length with live resize while typing
- Per-word GT commit behavior: persist on blur and Enter
- Per-word GT keyboard navigation: Tab to next word, Shift+Tab to previous word
- Word tag editing: dedicated `WordOperations` class for style label, scope, and component mutations
- Word tag editing: `SelectedWordOperationsProcessor` bridging backend operations with UI selection model
- Word tag editing: toolbar style/scope/component controls (dropdowns + apply/clear buttons)
- Word tag editing: tag chip display in word match grid and word edit dialog (with hover-close removal)
- Word tag editing: unified footnote marker behavior (LFN/RFN merged into single FN toggle)
- Word tag editing: migration from `word_labels` list to `text_style_labels` /
  `text_style_label_scopes` / `word_components` model
- Ground truth PGDP preprocessing: raw `pages.json` text preprocessed via
  `PGDPResults` at load time (diacritics, dashes, footnotes, quotes, proofer
  notes)
- Per-word validation state with line/paragraph rollup, UI toggle, and
  persistence across save/load and auto-cache
- Word edit dialog with interactive zoom slider (0.5x--2.0x) for image
  inspection and split marker alignment

## Remaining

### BBox Editing

- Add-word workflow: draw a bbox on the image to insert a new word (default target: nearest line/paragraph)
- Expand-bbox action for selected word(s)

### Block/Line Editing

- Additional line/paragraph refinement workflows

## Ground Truth and State

- ~~Persist and restore line validation + word GT fields~~ (Done — validation
  persisted via `word_attributes` sidecar; GT fields round-trip through
  save/load)
