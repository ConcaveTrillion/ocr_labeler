# Duplicated Code

Methods, constants, and patterns that appear multiple times in the
codebase and should be consolidated.

## Duplicated Constants

### `WORD_LABEL_*` constants — 3 definitions

| Constant | Location 1 | Location 2 | Location 3 |
| --- | --- | --- | --- |
| `WORD_LABEL_ITALIC` | `word_match.py` L52 | `word_match_gt_editing.py` L20 | `page_operations.py` L53 |
| `WORD_LABEL_SMALL_CAPS` | `word_match.py` L53 | `word_match_gt_editing.py` L21 | `page_operations.py` L54 |
| `WORD_LABEL_BLACKLETTER` | `word_match.py` L54 | `word_match_gt_editing.py` L22 | `page_operations.py` L55 |

`WORD_LABEL_LEFT_FOOTNOTE` / `WORD_LABEL_RIGHT_FOOTNOTE` also duplicated
between `word_match.py` and `word_match_gt_editing.py`.

**Fix**: Centralize in a constants module (`ocr_labeler/constants.py` or
`ocr_labeler/models/constants.py`).

### `WordKey` type alias — 5 definitions

- `word_match.py` L32 (with `TypeAlias`)
- `word_match_renderer.py` L28
- `word_match_selection.py` L13
- `word_match_gt_editing.py` L17
- `word_match_bbox.py` L17

**Fix**: Define once in `word_match.py` and import elsewhere.

### `ClickEvent` type alias — 4 definitions

- `word_match.py` L39
- `word_match_renderer.py` L29
- `word_match_gt_editing.py` L18
- `word_match_bbox.py` L18

**Fix**: Define once in `word_match.py` and import elsewhere.

### Image extension set `{".png", ".jpg", ".jpeg"}`

Appears in 3+ persistence files. Should be a shared constant.

## Duplicated Methods

### `get_cropped_image` — 2 copies (~60 lines each)

- `word_match_model.py` L69
- `line_match_model.py` L116

Nearly identical normalize → scale → clamp → slice pipeline.

**Fix**: Extract to a shared utility function in operations or models.

### `_word_bbox` / `_line_bbox` / `_paragraph_bbox` — 3 structural copies

- `image_tabs.py` L714–790

All three follow the same pattern: get bounding_box, check
is_normalized, resolve page dimensions, scale if needed, return tuple.
Only the input type differs.

**Fix**: Single `_element_bbox(element, page)` method.

### `copy_ground_truth_to_ocr` / `copy_ocr_to_ground_truth`

- `line_operations.py` L49–139

~90 lines duplicated with only source/target fields swapped.

**Fix**: Single `_copy_text_between_fields(source_attr, target_attr)`
method.

### `_is_geometry_normalization_error`

- `line_operations.py`
- `page_operations.py`

Identical implementation in both files.

### `_reorganize_page_if_available`

- `ocr_service.py`
- `page_operations.py`

Same purpose, different implementations.

### `_get_predictor` / `_get_or_create_predictor`

- `ocr_service.py`
- `page_operations.py`

Identical logic.

### `validate_project_directory`

- `project_discovery_operations.py`
- `project_operations.py`

Both check the same thing differently.

### `_resolve_workspace_save_directory`

- `page_state.py`
- `project_state.py`

Identical implementation.

### `queue_notification` / `pop_notification`

- `app_state.py`
- `project_state.py`

Near-identical with thread locks.

### `current_ocr_text` / `current_gt_text` / `_invalidate_text_cache`

- `page_state.py`
- `project_state.py`

Duplicated with different implementations.

### OS dispatch pattern (3 copies)

- `persistence_paths_operations.py`

Same `platform.system()` switch repeated 3 times for different paths.

### YAML template (2 copies)

- `config_operations.py`

Duplicated between `_default_config_contents` and
`set_source_projects_root`.

## Duplicated Patterns

### Selection snapshot/restore — ~25 repetitions

**File**: `word_match_actions.py`

Nearly every action handler follows this 30-line pattern:

1. Save 3 selection sets (line, word, paragraph)
2. Clear all 3 selections
3. Update button state + emit events
4. Try operation
5. On failure: restore all 3 + update + emit
6. On exception: restore all 3 + update + emit (same code again)

Methods that duplicate this pattern: `_handle_merge_selected_lines`,
`_handle_merge_selected_paragraphs`,
`_handle_delete_selected_paragraphs`,
`_handle_split_paragraph_after_selected_line`,
`_handle_split_paragraph_by_selected_lines`,
`_handle_split_line_after_selected_word`,
`_handle_delete_selected_words`, `_handle_merge_selected_words`,
`_handle_refine_selected_words`, `_handle_refine_selected_lines`,
`_handle_expand_then_refine_selected_words`,
`_handle_expand_bbox_selected_words`,
`_handle_expand_then_refine_selected_lines`, and ~12 more.

**Fix**: Extract to a context manager or helper like
`_with_selection_snapshot(callback, success_msg, fail_msg)`.

### 25+ structural editing boilerplate methods

**File**: `page_state.py` L1000–2200

All follow identical pattern: null-check → deferred import
`LineOperations` → instantiate → call method →
`_finalize_structural_edit()`.

**Fix**: Generic dispatch helper that takes method name and args.

### 30+ pure delegation methods

**File**: `word_match.py` L1120–1430

Each method is just: `"""Delegate."""; self.actions._handle_X(_event)`.
The toolbar already calls `self._view.actions._handle_*` directly.

**Fix**: Eliminate wrappers; have renderer call
`self._view.actions.*` directly.

### 35+ callback closures in `__init__`

**File**: `text_tabs.py` L100–780

Each closure wraps a single `page_state.method(page_index, ...)` call.
~680-line `__init__` method.

**Fix**: Callback builder helper:
`_bind(method_name, *extra_args)`.

### `_notify()` / `_notify_once()` — 5 copies

Appears in: `project_load_controls.py`,
`project_navigation_controls.py`, `project_view.py`, `page_actions.py`,
`image_tabs.py`.

**Fix**: Move to `BaseView` or a shared mixin.

### `_bind_from_safe` / `_bind_disabled_from_safe` — 2 copies

- `project_load_controls.py`
- `project_navigation_controls.py`

~40 lines duplicated.

**Fix**: Move to shared utility or `BaseView`.

## Dead Code

- **`NotificationService`** (`services/notification_service.py`): Entire
  class is never used anywhere in the codebase
- **`_resolve_text`** (`doctr_export.py` L620): Never called
- **`_resolve_bbox`** (`doctr_export.py` L627): Never called
- **`train_val_split`** parameter in `DocTRExportOperations.__init__`:
  Stored but never used
- **Logger** in `project_model.py`: Defined but never used
