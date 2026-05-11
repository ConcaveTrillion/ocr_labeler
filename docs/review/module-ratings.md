# Per-Module Quality Ratings

Scale: 5 = clean and correct; 1 = significant defects requiring attention.

## Top-Level

| File | Rating | Primary issue |
| --- | --- | --- |
| `__init__.py` | 5/5 | Correct barrel export |
| `constants.py` | 5/5 | Trivially small, correct |
| `prefetch.py` | 4/5 | `logging.basicConfig` called inside `main()` — side effect if imported |
| `local_state_cleanup.py` | 4/5 | `_merge` mutates in-place and returns — inconsistent contract |
| `cli.py` | 3/5 | `logger.info` emitted before `dictConfig` is applied; default log handler is a null handler (silences errors from operators); stale `--font-name/--font-path` help text |
| `routing.py` | 3/5 | `build_project_url` has no URL encoding (bug); implicit page-1 default return value is confusing |
| `app.py` | 2/5 | Cross-session log contamination; repeating timer without `once=True`; Referer-based routing fallback |

## Models

| File | Rating | Primary issue |
| --- | --- | --- |
| `models/__init__.py` | 5/5 | Correct barrel |
| `models/line_match_model.py` | 4/5 | `overall_match_status` conflates UNMATCHED and MISMATCH; inconsistent `get_cropped_image` API vs `WordMatch` |
| `models/word_match_model.py` | 4/5 | `word_object: object` loses type info; float/NaN hash edge case |
| `models/project_model.py` | 3/5 | `to_dict`/`from_dict` serializes navigation state; `total_pages` is a mutable int that can drift |
| `models/user_page_persistence.py` | 3/5 | Silent fallback class definitions if `pd_book_tools` import fails; duplicate type aliases (`ProvenanceOCRModel`/`OCRModelProvenance`) |
| `models/page_model.py` | 2/5 | Property/backing-field contract is inconsistent; `__getattr__` proxy hides `AttributeError` and breaks static analysis; exception silencing on setter |

## State

| File | Rating | Primary issue |
| --- | --- | --- |
| `state/__init__.py` | 5/5 | Correct barrel |
| `state/app_state.py` | 2/5 | Three identical model option dicts; `_default_project_state` stored via `setattr` anti-pattern; `is_loading.setter` doesn't call `notify()`; `__post_init__` has `# pragma: no cover` |
| `state/project_state.py` | 2/5 | Hardcoded dev path default; `ensure_page_model` is 430+ lines; multiple `.name` accesses without None guard; cross-access to `PageState` private methods |
| `state/page_state.py` | 1/5 | 2,650 lines; `@notify_on_completion` triple-fire; listener cycle risk with `ProjectState`; 11× `logger.critical` for routine guard conditions; property getter fires `notify()`; two parallel snapshot methods (index-keyed vs id-keyed) where only one is correct for all cases |

## Services

| File | Rating | Primary issue |
| --- | --- | --- |
| `services/__init__.py` | 5/5 | Correct barrel |
| `services/notification_service.py` | 1/5 | Entirely dead code; log-severity misuse; unimplemented TODO |

## Operations — OCR

| File | Rating | Primary issue |
| --- | --- | --- |
| `operations/ocr/word_operations.py` | 4/5 | Dead re-export constants; fuzz score returns `0.0` when unavailable (ambiguous vs computed 0) |
| `operations/ocr/image_cache_operations.py` | 4/5 | `max(-1, int(page_index))` lower bound is never useful; broad `object` type annotations |
| `operations/ocr/bbox_operations.py` | 3/5 | Partial-apply bug on validation failure; `BboxOperations()` re-instantiated per dispatch |
| `operations/ocr/line_operations.py` | 3/5 | Aliasing assumption when fetching `line_words` vs `lines[line_index]`; API inconsistency with `page_operations._apply_word_attributes_to_page` |
| `operations/ocr/model_selection_operations.py` | 3/5 | Unreachable `"hf-only"` branch; blocking HF network calls at startup |
| `operations/ocr/navigation_operations.py` | 3/5 | Dead `schedule_navigation`; `next_page`/`prev_page` return only bool, not the new index |
| `operations/ocr/text_operations.py` | 2/5 | UI display strings (`"LOADING..."`, `"LABELED"`) returned from operations layer; GT lookup only by `page.name` (may miss keys) |
| `operations/ocr/page_operations.py` | 2/5 | Crash in `can_load_page` exception handler; double-parse of envelope; variable shadowing; memory leak; 1,800-line god class; `TYPE_CHECKING: pass` dead block |
| `operations/ocr/ocr_service.py` | 1/5 | Entirely dead code; fake-async; duplicates page_operations |

## Operations — Persistence

| File | Rating | Primary issue |
| --- | --- | --- |
| `operations/persistence/session_state_operations.py` | 5/5 | Clean |
| `operations/persistence/project_discovery_operations.py` | 3/5 | Hardcoded extension literal instead of `IMAGE_EXTS`; validation logic duplicated from `list_available_projects` |
| `operations/persistence/config_operations.py` | 3/5 | Hand-rolled YAML parser breaks on values with colons; `CONFIG_PATH` global mutable class var |
| `operations/persistence/persistence_paths_operations.py` | 3/5 | 40-line duplication between `get_config_root` and `get_data_root`; `cwd()` vs `project_root` resolution inconsistency |
| `operations/persistence/project_operations.py` | 2/5 | `reload_ground_truth_into_project` reaches into `AppState` from persistence layer; hardcoded extension literal; `load_project_metadata` validates but ignores result |

## Operations — Export

| File | Rating | Primary issue |
| --- | --- | --- |
| `operations/export/cli.py` | 4/5 | Unconditional `return 0` even on export errors |
| `operations/export/doctr_export.py` | 3/5 | Staleness check path mismatch (always wrong); `_prepare_page_gt_first` permanently mutates live page in GUI path |

## ViewModels

| File | Rating | Primary issue |
| --- | --- | --- |
| `viewmodels/shared/base_viewmodel.py` | 3/5 | No teardown hook; manual pub-sub alongside NiceGUI binding |
| `viewmodels/app/app_state_view_model.py` | 3/5 | `update()` sets 13 properties sequentially — each fires notification (13 partial-state events per change); no teardown |
| `viewmodels/project/project_state_view_model.py` | 3/5 | Generic `"project_state"` event never matches `MainViewModel` listener; dead `can_navigate_override`; `_update_navigation_properties` called twice in `set_action_busy` |
| `viewmodels/project/word_match_view_model.py` | 3/5 | Mock-defensive guards in production code; `get_summary_stats()` dead query API |
| `viewmodels/main_view_model.py` | 2/5 | Writes private attributes across VM boundaries; listener leak on `ProjectState` switch; `super().__init__()` after child VM construction |
| `viewmodels/project/page_state_view_model.py` | 2/5 | `_update_image_sources_async` and `_update_image_sources_blocking` share 90% of logic; `logger.info` in per-navigation hot path; dead `_image_mappings` abstraction; triple update flag state machine |

## Views

| File | Rating | Primary issue |
| --- | --- | --- |
| `views/shared/button_styles.py` | 4/5 | `active` flag is a no-op for `DEFAULT` variant |
| `views/shared/view_helpers.py` | 4/5 | `_app_state_view_model: Any = None` class-level default loses type safety |
| `views/callbacks.py` | 4/5 | `PageActionEvent` defined here and again in `page_view.py` |
| `views/projects/project_navigation_controls.py` | 4/5 | Lambda captures `self.page_input` before it is assigned |
| `views/shared/base_view.py` | 3/5 | `teardown()` is never called; `_on_viewmodel_property_changed` is not abstract |
| `views/header/header.py` | 4/5 | `_on_viewmodel_property_changed` not overridden — silently drops all property events |
| `views/header/ocr_config_modal.py` | 3/5 | `self.app_state_model` and `self._app_state_view_model` are the same object under two names; `_open` is `async` with no `await` |
| `views/main_view.py` | 3/5 | Accesses `project_view._root` private field; `refresh()` called multiple times per notify cycle; dead `elif: pass` branch |
| `views/projects/pages/export_dialog.py` | 3/5 | Blocking `load_all_saved_pages()` in async handler; emoji in label strings |
| `views/projects/pages/page_actions.py` | 3/5 | Same binding key for 7 buttons (only first failure notifies user); `ui.button` used as display-only label |
| `views/projects/pages/content.py` | 3/5 | Raw `PageState` passed to `TextTabs`; `_safe_notify` private method called from sibling view |
| `views/projects/project_view.py` | 2/5 | Duplicate `_action_context`; dead `_show_busy_spinner` tracking; `getattr` for non-existent viewmodel properties; private `_project_state` access |
| `views/header/project_load_controls.py` | 2/5 | Embedded filesystem browser; `mkdir` side effect in view; same binding key for 4 controls |
| `views/projects/pages/page_view.py` | 2/5 | Duplicate `_action_context`; 14× `asyncio.sleep(0.1)` without documentation; duplicate `_reload_ocr_async/edited` handlers; custom notification routing bypassing `NotificationMixin` |
| `views/projects/pages/image_tabs.py` | 2/5 | 1,101 lines; triplicated drag emit helpers; triplicated drag state machines; dead `tab_name` parameter; private `_page_state` access 8+ times |
| `views/projects/pages/text_tabs.py` | 2/5 | 300-line constructor; couples directly to `PageState`; business logic (fingerprinting) inside view; correctness depends on listener registration order |
