# Layer Violations

Methods and code that live in the wrong architectural layer, violating
the MVVM pattern or operations/state/model boundaries.

## Business Logic in State Layer

| Method | File | Issue |
| --- | --- | --- |
| `toggle_word_validated()` | `page_state.py` L457 | Directly manipulates `word.word_labels` instead of delegating to operations |
| `current_page_source_text` | `page_state.py` L731 | Returns display strings ("LABELED", "CACHED OCR") — presentation belongs in viewmodel |
| `current_page_source_tooltip` | `page_state.py` L770 | Returns tooltip text — presentation concern |
| `current_page_export_status` | `page_state.py` L807 | Returns "EXPORTED"/"EXPORT STALE" — presentation concern |
| `SaveProjectResult.summary` | `project_state.py` L42 | Display formatting in a state-layer dataclass |
| `export_current_page()` | `project_state.py` L1115 | Full save + validation + export orchestration — business logic |
| `export_all_validated_pages()` | `project_state.py` L1226 | Same export orchestration |
| `create_fallback_page()` | `project_state.py` L1694 | Does `cv2` image loading — I/O in state |
| `_navigate()` | `project_state.py` L889 | Uses `background_tasks.create()` — NiceGUI-specific async in state |
| `load_project()` | `app_state.py` L110 | Session state persistence done inline (L148–155) |

## UI Framework Dependencies in State

- `page_state.py` L74–76: `on_word_ground_truth_change`,
  `on_word_style_change`, `on_word_validation_change` use `nicegui.Event`
  type — state layer should not depend on UI framework types

## Operations Reaching Into State

- `project_operations.py` `reload_ground_truth_into_project()`: Takes
  `AppState` and calls `state.notify()`,
  `state._invalidate_text_cache()`. Operations should return results; the
  caller (state or viewmodel) should handle notification.

## UI Display Strings in Operations

- `text_operations.py` `get_page_source_text()`: Returns display strings
  ("LOADING...", "LABELED", "RAW OCR"). Should return an enum or status
  code that the presentation layer maps to display text.
- `text_operations.py` `get_loading_text()`: Returns hardcoded UI
  placeholder strings.

## Image Processing in Model Layer

- `word_match_model.py` `get_cropped_image()` L69: numpy array
  manipulation with coordinate math — image operations, not model
  concern
- `line_match_model.py` `get_cropped_image()` L116: Same issue

## Operations Re-exported from State Package

- `state/__init__.py` L1–2: `PageOperations` and `ProjectOperations`
  re-exported from the state package. Misleading package membership.

## Image Processing in ViewModel Layer (Critical)

`page_state_view_model.py` contains ~300 lines of image resizing
(`cv2.resize`), encoding (`cv2.imencode`), color space conversion
(`cv2.cvtColor`), disk I/O, hash computation (MD5), and thread pool
management. All should be extracted to an `ImageCacheOperations` class in
the operations layer.

## Business Logic in View Layer

| Method | File | Issue |
| --- | --- | --- |
| `apply_local_word_gt_update` | `word_match_renderer.py` L1085 | Full match-status classification algorithm (exact/fuzzy/mismatch threshold) |
| `_build_word_match_from_word_object` | `word_match_renderer.py` L1150 | Duplicates `WordMatch` construction logic from ViewModel |
| `compute_refine_preview_deltas` | `word_match_bbox.py` L213 | Calls `bbox.refine(page_image, ...)` — geometry/image operations |
| `get_line_image` | `word_match_bbox.py` L1010 | OpenCV image cropping and encoding |
| `_stage_crop_to_marker` | `word_edit_dialog.py` | ~100 lines of geometric bbox calculation per direction |
| `clear_scope_on_word` | `word_operations.py` (views) L210-252 | Directly mutates `word_object.text_style_label_scopes` |
| `_apply_style` | `word_operations.py` (views) L80-143 | Mixed view+operations logic; word-object mutation belongs in operations |
| `get_word_image_slice` | `word_match_bbox.py` L47-155 | Coordinate math for cropping from page images |

## Views Accessing State Directly (Bypassing ViewModels)

| View | Access Pattern | Location |
| --- | --- | --- |
| `TextTabs` | Receives raw `PageState`, creates ~30 closures calling `page_state.merge_lines()` etc. directly | `text_tabs.py` `__init__` |
| `ContentArea` | `page_state_view_model._page_state` — private access | `content.py` L28 |
| `ImageTabs` | `getattr(self.page_state_view_model, "_page_state", None)` throughout | `image_tabs.py` multiple |
| `PageView.refresh()` | `project_view_model._project_state.project.image_paths` — 3 levels deep | `page_view.py` L105–108 |
| `PageView._sync_text_tabs()` | Sets `text_tabs.page_state.current_page` and calls private `_update_text_editors()` | `page_view.py` L161 |
| `PageView._sync_browser_url()` | `self.viewmodel._project_state` — private access | `project_view.py` L289 |

## Views Reaching Through ViewModel Privates for Notifications

Found in 5 places — all access `_app_state_model._app_state` to call
`queue_notification()`:

- `main_view.py` L160
- `project_load_controls.py` L41
- `project_view.py` L111
- `project_navigation_controls.py` L33
- `page_actions.py` L53

**Fix**: Add `queue_notification()` and `pop_notification()` as public
methods on `AppStateViewModel`.

## ViewModels Bypassing Operations

| Method | File | Issue |
| --- | --- | --- |
| `command_select_project` L120 | `app_state_view_model.py` | Directly sets `_app_state.selected_project_key` and calls notify() |
| `source_projects_root_str` L104 | `app_state_view_model.py` | Calls `ConfigOperations.get_source_projects_root()` directly |
| `_create_word_match` L225 | `word_match_view_model.py` | Match-status classification logic — should be in operations |
| `_build_line_paragraph_lookup` L126 | `word_match_view_model.py` | Page tree traversal logic |

## ViewModels Violating Encapsulation

| Violator | Access | Location |
| --- | --- | --- |
| `MainViewModel._on_app_state_changed` | `self.app_state_view_model._app_state.project_state` | `main_view_model.py` L80–105 |
| `ProjectStateViewModel.__init__` | `self._app_state_model._app_state.on_change.append(...)` | `project_state_view_model.py` L66 |
| `ProjectState` | Calls `page_state._refresh_page_overlay_images()` and `page_state._auto_save_to_cache()` (private) | `project_state.py` L1480–1524 |

## Views Directly Mutating Model Objects

- `word_match_gt_editing.py` `_apply_local_word_style_update` L407:
  Mutates `word_object` attributes directly
- `word_operations.py` (views) `clear_scope_on_word` L225: Directly
  mutates `word_object.text_style_label_scopes`
- `word_match_renderer.py` `apply_local_word_gt_update`: Mutates
  `word_match.ground_truth_text`, `match_status`, `fuzz_score`

## Views Not Extending `BaseView`

- `ProjectLoadControls` and `ProjectNavigationControls` are plain
  classes, not `BaseView` subclasses. No lifecycle management, no
  teardown.

## Missing Listener Cleanup

- `base_view.py`: `BaseView.__init__` registers a listener but has no
  `teardown()`/`dispose()` method. When views are destroyed and
  recreated, orphaned listeners accumulate → callback leak.

## Renderer Cross-Object State Mutation

- `word_match_renderer.py` `update_lines_display` L96-145: Clears 15+
  dictionaries on `self._view` (parent view). The renderer should not
  reach into and mutate the parent's internal state.

## `PageView` Reaches Through Object Chains

- `page_view.py` L103-120: Reaches through
  `project_view_model._project_state.project.image_paths` — three levels
  deep into private attributes.
