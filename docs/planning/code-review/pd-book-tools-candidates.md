# pd-book-tools Migration Candidates

Code in ocr-labeler that operates generically on `Page`, `Block`, `Word`,
and `BoundingBox` objects without app-specific dependencies. These are
candidates for migration to the pd-book-tools library.

## Bbox-to-Image Crop Pipeline

The normalize → scale → clamp → slice pipeline in `get_cropped_image`
(`word_match_model.py` L69, `line_match_model.py` L116) is generic
image/OCR work.

**Proposed API**: `BoundingBox.crop(image: np.ndarray) -> np.ndarray`

## Structural Page Operations (from `LineOperations`)

These are pure operations on `Page`/`Block`/`Word` structures with no
app-specific dependencies:

- `merge_lines` — generic block merging
- `delete_lines` — generic block deletion
- `merge_paragraphs` — generic paragraph merging
- `delete_paragraphs` — generic paragraph deletion
- `split_paragraphs` — generic paragraph splitting
- `split_word` — word splitting with bbox calculation
- `rebox_word` — word bbox replacement
- `add_word_to_page` — word insertion with line assignment

## Bbox Refinement/Expansion Methods

All bbox refinement and expansion operations from `LineOperations`:

- `refine_words`
- `expand_word_bboxes`
- `refine_lines`
- `refine_paragraphs`
- All variants of expand-then-refine

## Geometry Helpers (from `LineOperations`)

Spatial search and bbox geometry utilities:

- `_bbox_vertical_midpoint`, `_bbox_horizontal_midpoint`,
  `_bbox_y_range` — bbox geometry
- `_closest_line_by_y_range_then_x`,
  `_closest_line_by_midpoint` — spatial search
- `_recompute_nested_bounding_boxes` — recursive bottom-up bbox
  recompute
- `_find_parent_block`, `_remove_nested_block` — block hierarchy
  navigation
- `_has_usable_bbox`, `_first_usable_bbox` — bbox validation
- `_remove_empty_items_safely`,
  `_prune_empty_blocks_fallback` — structure cleanup

## Word Style Adapter

`WordOperations` (`operations/ocr/word_operations.py`) bridges legacy
boolean attributes to modern label-based styles. If pd-book-tools
standardized its `Word` API with a single style system, this adapter
would be unnecessary.

## Text Copy Between Fields

`copy_ground_truth_to_ocr` / `copy_ocr_to_ground_truth` in
`line_operations.py` — generic field-to-field copy on Word objects.

## Priority

| Priority | Item | Reason |
| --- | --- | --- |
| High | Structural operations (merge/split/delete) | Most impact, most lines |
| High | Bbox refinement/expansion | Performance-critical, frequently used |
| Medium | Geometry helpers | Many callers across the codebase |
| Medium | Bbox crop pipeline | Eliminates duplication in 2 model files |
| Low | Word style adapter | Requires API redesign in pd-book-tools |
| Low | Text copy methods | Small, simple migration |
