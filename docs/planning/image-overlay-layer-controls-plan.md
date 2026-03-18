# Plan: Unified Image Overlay Layers and Selection Mode Controls

## Summary

Replace the current multi-tab image experience (`Original`, `Paragraphs`, `Lines`, `Words`, `Mismatches`) with a single image viewport that supports:

- Layer visibility checkboxes for paragraph, line, and word bounding boxes.
- A radio-button selection mode switch for active selection target (`paragraph`, `line`, `word`).
- Existing drag-select behavior, mapped to the selected mode.
- Existing right-panel synchronization (selection and action availability), without regressing current edit workflows.

## Why This Change

Current tab-based visualization forces users to switch tabs to compare overlays. A unified viewport keeps context stable while allowing quick layer toggling and explicit selection intent, which should reduce interaction cost during labeling and refinement.

## Current Implementation Notes

- Left-side image UI is currently in `ocr_labeler/views/projects/pages/image_tabs.py`.
- Image rendering uses tab-specific images and interactive overlays (`Words`, `Lines`, `Paragraphs`) with drag handlers.
- Right-panel selection synchronization is already wired in `ocr_labeler/views/projects/pages/content.py` and `ocr_labeler/views/projects/pages/word_match.py`.
- Page layout and splitter composition is in `ocr_labeler/views/projects/pages/content.py`.

This means most of the selection/event plumbing already exists and can be reused.

## UX Proposal

### Viewport

- Single interactive image viewport on the left panel.
- Base image: original page image.
- Overlay layers drawn in distinct colors:
  - Paragraph boxes.
  - Line boxes.
  - Word boxes.
- Selected entities rendered with stronger fill/stroke contrast.

### Controls

- `ui.checkbox` controls:
  - `Show Paragraphs` (default: on)
  - `Show Lines` (default: on)
  - `Show Words` (default: on)
- `ui.radio` selection mode control:
  - `Select Paragraphs`
  - `Select Lines`
  - `Select Words` (default)
- Optional later control (not required in first pass): `Show only selected`.

### Interaction Behavior

- Drag box always applies to whichever radio mode is active.
- Ctrl-drag adds to current selection.
- Shift-drag removes from current selection.
- Right-panel checkbox interactions continue to update the left overlay highlights.
- Word rebox mode remains word-scoped and temporarily overrides radio mode while active.

## Technical Approach

### Preferred Rendering Strategy

Use a single `ui.interactive_image` and render SVG overlays client-side via `interactive_image.content`.

- Keep one source image (original).
- Compute scaled bbox coordinates for each layer from page model data.
- Render overlay SVG fragments conditionally by checkbox state.
- Render selected boxes from existing selection sets.

This avoids loading and switching among multiple pre-rendered bbox images and makes layer compositing straightforward.

### Data/State Additions

Add UI-local state in the image view component:

- `visible_layers: dict[str, bool]` for `paragraphs`, `lines`, `words`.
- `selection_mode: Literal["paragraph", "line", "word"]`.
- Existing selected sets remain:
  - `selected_paragraph_indices`
  - `selected_word_indices` (line selection continues deriving from word set or explicit line set helper)

No persistence changes required initially (session-only UI controls).

## Image Cache Strategy

For this redesign, prefer reducing cache surface area:

- Keep only one base page image source in the left viewport.
- Stop depending on pre-rendered per-layer raster images for display (`paragraph_with_bboxes`, `line_with_bboxes`, `word_with_bboxes`).
- Render all layer boxes as SVG overlays in the client.

### Recommended Policy

1. Reuse existing cache root and cleanup behavior.
2. Do not add any new overlay-specific disk cache files for this feature.
3. Keep compatibility with old cached image filenames while migrating.
4. Keep cache invalidation on forced OCR reload unchanged.

### Migration Details

- Read path:
  - Prefer original/base image source for the viewport.
  - If legacy layer-raster caches exist, ignore them for rendering overlays in the new UI.
- Write path:
  - Do not write new paragraph/line/word overlay raster files for the unified overlay path.
  - Continue writing any existing required artifacts for backward compatibility only during transition.
- Cleanup path:
  - Continue using current page-level cache invalidation and stale-file cleanup.
  - Add an optional one-time garbage-collection task to delete obsolete legacy overlay raster files after migration is stable.

### Why This Is Better

- Lower disk churn and smaller cache footprint.
- No risk of stale overlay rasters diverging from current page geometry.
- Faster feature iteration (overlay style/opacity/selection visuals can change without cache format changes).

### Acceptance Criteria for Cache Behavior

- Unified overlay view renders correctly with only base image plus client-side SVG overlays.
- No new overlay-specific cache files are created by normal selection/layer toggle interactions.
- Forced OCR reload still invalidates page image cache entries for that page.
- Legacy cached layer rasters do not break rendering and can be safely ignored.

## File-Level Plan

### 1) Introduce unified overlay component

- Replace/refactor `ImageTabs` in `ocr_labeler/views/projects/pages/image_tabs.py` into a single-overlay view (can keep class name initially for low-risk migration, then rename later).
- Remove tab definitions and per-tab interactive images.
- Add controls row (checkboxes + radio) above viewport.
- Keep existing drag lifecycle methods (`mousedown/mousemove/mouseup`) but route selection by current radio mode.

### 2) Keep selection sync contract stable

- Preserve public methods used by `ContentArea`:
  - `set_selected_words(...)`
  - `set_selected_paragraphs(...)`
  - word rebox enable/disable and callback emission.
- Ensure callbacks still emit:
  - selected words to right panel.
  - selected paragraphs to right panel.
- For line mode, continue expanding selected lines to words when notifying right panel, or add dedicated line callback only if needed.

### 3) Update layout usage

- In `ocr_labeler/views/projects/pages/content.py`, keep left-panel composition the same but expect a single viewport rather than tabs.
- Ensure image updates from `set_image_update_callback` still update base image source and trigger overlay redraw.

### 4) Backward-compatible migration guard

- Keep old class APIs where practical to avoid broad touching of page/content view code.
- If renaming class/file, include a thin adapter layer for one iteration.

### 5) Test updates

- Unit test overlay rendering state transitions:
  - toggling each layer affects rendered SVG fragments.
  - radio mode changes selection target.
- Unit/integration tests for selection propagation:
  - image drag in each mode updates right-panel selection as expected.
  - right-panel selection still updates overlay highlights.
- Regression tests for rebox flow in word mode.

## Implementation Phases

1. Build unified viewport scaffold with controls and base image rendering.
2. Port overlay drawing for all three bbox layers.
3. Wire radio-mode drag selection behavior.
4. Reconnect right-panel sync and verify action enablement behavior.
5. Remove dead tab-specific code paths and clean up naming.
6. Add/adjust tests and documentation.

## Acceptance Criteria

- User can view any combination of paragraph/line/word overlays simultaneously.
- User can switch selection mode via radio buttons and drag-select only that entity type.
- Ctrl/Shift additive/subtractive selection behavior works in all modes.
- Existing right-panel operations still receive correct selection context.
- Word rebox workflow still works.
- No page navigation regressions or stale overlay artifacts.

## Risks and Mitigations

- Risk: overlay redraw cost on large pages.
  - Mitigation: cache computed display-scale boxes and redraw only on selection/layer changes.
- Risk: ambiguity in line selection representation.
  - Mitigation: keep line selection as derived from selected words for compatibility in first pass.
- Risk: interaction conflicts between rebox mode and generic selection mode.
  - Mitigation: explicit temporary rebox override with visible UI indicator.

## Open Questions

- Should line selection be first-class state (`selected_line_indices`) on the image side, or remain derived from word selections?
- Should layer visibility and selection mode persist per user/session?
- Should mismatch visualization remain as a separate optional overlay layer in this same viewport?

## Suggested Follow-up Tasks

- Add a compact legend chip row that maps color to layer type.
- Add keyboard shortcuts:
  - `1` word mode, `2` line mode, `3` paragraph mode.
  - `W/L/P` layer visibility toggles.
- Add an optional opacity slider for overlays.

## Implementation Ticket Draft

### EPIC: Unified Image Overlay View

#### Ticket 1: Build single viewport scaffold and controls

- Scope:
  - Refactor left panel image area to one interactive viewport.
  - Add layer visibility checkboxes (paragraph, line, word).
  - Add selection-mode radio control (paragraph, line, word).
- Files:
  - `ocr_labeler/views/projects/pages/image_tabs.py`
  - `ocr_labeler/views/projects/pages/content.py`
- Done when:
  - One viewport renders and controls appear.
  - Selection mode changes internal state.

#### Ticket 2: Port overlay rendering to SVG layers

- Scope:
  - Draw paragraph/line/word boxes in SVG overlay content.
  - Render selected entities with stronger highlight style.
  - Honor layer checkboxes in render output.
- Files:
  - `ocr_labeler/views/projects/pages/image_tabs.py`
- Done when:
  - Any combination of layers can be shown simultaneously.
  - Visual state remains stable during mouse drag.

#### Ticket 3: Route drag selection by radio mode

- Scope:
  - Keep existing drag lifecycle and modifier semantics.
  - Apply selection to paragraph/line/word based on active mode.
  - Keep rebox override behavior for word rebox interactions.
- Files:
  - `ocr_labeler/views/projects/pages/image_tabs.py`
  - `ocr_labeler/views/projects/pages/word_match.py`
- Done when:
  - Drag selection updates the intended entity type only.
  - Ctrl/Shift add/remove behavior works in all modes.

#### Ticket 4: Preserve right-panel synchronization and actions

- Scope:
  - Keep existing selection callback contracts compatible.
  - Ensure left-panel selection updates right-panel checkboxes.
  - Ensure right-panel selection updates left overlay highlights.
- Files:
  - `ocr_labeler/views/projects/pages/content.py`
  - `ocr_labeler/views/projects/pages/image_tabs.py`
  - `ocr_labeler/views/projects/pages/word_match.py`
- Done when:
  - Existing line/word/paragraph actions remain enabled/disabled correctly.

#### Ticket 5: Cache migration and legacy artifact handling

- Scope:
  - Stop writing new per-layer overlay raster caches for unified overlay path.
  - Continue using base page image cache and invalidation behavior.
  - Ignore legacy layer rasters for rendering in the new UI.
- Files:
  - `ocr_labeler/views/projects/pages/image_tabs.py`
  - `ocr_labeler/state/page_state.py`
  - `ocr_labeler/operations/ocr/page_operations.py`
- Done when:
  - Unified overlay flow does not create new paragraph/line/word raster cache files.
  - Forced OCR reload still clears page cache entries.

#### Ticket 6: Tests and documentation

- Scope:
  - Add unit tests for layer toggle and selection mode behavior.
  - Add integration tests for bidirectional selection sync.
  - Add regression tests for rebox mode and cache behavior expectations.
  - Update docs where image view behavior is described.
- Files:
  - `tests/**` (new or updated view/state tests)
  - `docs/planning/image-overlay-layer-controls-plan.md`
  - `docs/architecture/**` (if implementation detail docs are updated)
- Done when:
  - New tests are green and existing tests remain green.
  - Plan and architecture docs reflect the unified overlay model.

## Commit Message Draft

Title:

- `docs(planning): add unified overlay migration checklist and cache strategy`

Body:

- `Document implementation ticket breakdown for unified image overlay UI`
- `Define cache migration policy: base image cache only, client-side SVG layers`
- `Specify compatibility behavior for legacy overlay raster cache artifacts`
