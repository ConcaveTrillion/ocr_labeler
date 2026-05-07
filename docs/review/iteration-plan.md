# Iteration Plan

Prioritised list of tasks for Opus to work through. Each item cites the relevant
`bugs.md`, `dead-code.md`, or `architecture.md` reference.

Items are grouped into four tiers. Work tier 1 before tier 2, etc.

---

## Tier 1 — Fix crashes and always-wrong results

These are bugs that either crash the application or silently produce wrong output.
They should be fixed before any structural work.

| # | Task | Reference | File(s) |
|---|---|---|---|
| 1 | Fix `can_load_page` exception handler (`Path(None)` crash) | bugs.md B1 | `operations/ocr/page_operations.py` |
| 2 | Fix `check_page_export_status` path mismatch | bugs.md B4 | `operations/export/doctr_export.py` |
| 3 | Add `once=True` to session-init timer | bugs.md B2 | `app.py` |
| 4 | Fix per-tab log handler proliferation | bugs.md B3 | `app.py` |
| 5 | Fix `bbox_operations` partial-apply on validation failure | bugs.md B5 | `operations/ocr/bbox_operations.py` |
| 6 | Fix navigation-derived properties never updating | bugs.md B6 | `viewmodels/project/project_state_view_model.py` |
| 7 | Add URL encoding to `build_project_url` | bugs.md C6 | `routing.py` |
| 8 | Fix `app_state.is_loading.setter` — add `notify()` | bugs.md C9 | `state/app_state.py` |

---

## Tier 2 — Fix memory leaks and major correctness bugs

| # | Task | Reference | File(s) |
|---|---|---|---|
| 9 | Replace `_saved_provenance_by_page_id` with `WeakKeyDictionary` | bugs.md ML1 | `operations/ocr/page_operations.py` |
| 10 | Wire `BaseView.teardown()` to session disconnect | bugs.md ML2 | `app.py`, `views/shared/base_view.py` |
| 11 | Add `BaseViewModel.teardown()` to remove `on_change` listeners | bugs.md ML2 | `viewmodels/shared/base_viewmodel.py`, all VMs |
| 12 | Fix `load_page_model` double-parse of `UserPageEnvelope` | bugs.md C1 | `operations/ocr/page_operations.py` |
| 13 | Fix `image_path` variable shadowing in `load_page_model` | bugs.md C2 | `operations/ocr/page_operations.py` |
| 14 | Remove `notify()` call from `_update_text_cache` | bugs.md C3 | `state/page_state.py` |
| 15 | Fix `@notify_on_completion` triple-fire on structural edits | bugs.md C4 | `state/page_state.py` |
| 16 | Fix hardcoded dev path in `project_state.py:69` | bugs.md C5 | `state/project_state.py` |
| 17 | Fix blocking HF network calls at startup | bugs.md C8 | `operations/ocr/model_selection_operations.py` |
| 18 | Fix `page_model.py:image_path` silent exception swallowing | bugs.md C10 | `models/page_model.py` |

---

## Tier 3 — Remove dead code

These are safe deletions with no functional impact. Do them as a batch.

| # | Task | Reference | File(s) |
|---|---|---|---|
| 19 | Delete `operations/ocr/ocr_service.py`; remove from `operations/__init__.py` | dead-code.md D1 | `operations/ocr/ocr_service.py` |
| 20 | Delete `services/notification_service.py`; update `services/__init__.py` | dead-code.md D2 | `services/notification_service.py` |
| 21 | Delete `NavigationOperations.schedule_navigation` and its test | dead-code.md D3 | `operations/ocr/navigation_operations.py` |
| 22 | Delete `operations/validation/` directory | dead-code.md D4 | `operations/validation/` |
| 23 | Remove dead re-exports from `word_operations.py` | dead-code.md D5 | `operations/ocr/word_operations.py` |
| 24 | Remove `ProjectStateViewModel.can_navigate_override` | dead-code.md D6 | `viewmodels/project/project_state_view_model.py` |
| 25 | Verify and delete `command_get_*` query methods on `MainViewModel` and `ProjectStateViewModel` | dead-code.md D7 | `viewmodels/main_view_model.py`, `project_state_view_model.py` |
| 26 | Delete commented-out `TextTabsModel.__setattr__` | dead-code.md D8 | `views/projects/pages/text_tabs.py` |
| 27 | Remove `# pragma: no cover` from `AppState.__post_init__` | dead-code.md D9 | `state/app_state.py` |

---

## Tier 4 — Structural refactoring

These are larger refactors that improve long-term maintainability. Work through
them one at a time, with tests before and after.

| # | Task | Reference | File(s) |
|---|---|---|---|
| 28 | Consolidate image extension constant — replace 4 literals with `IMAGE_EXTS` | architecture.md A6 | `project_operations.py`, `project_discovery_operations.py`, `page_operations.py`, `doctr_export.py` |
| 29 | Expose public `current_page` property on `PageStateViewModel`; eliminate all `._page_state` private accesses in views | architecture.md A2 | `page_state_view_model.py`, `image_tabs.py`, `content.py`, `text_tabs.py` |
| 30 | Expose `rebind(new_project_state)` on `ProjectStateViewModel`; eliminate `MainViewModel` cross-VM private mutation | architecture.md A2 | `viewmodels/main_view_model.py`, `viewmodels/project/project_state_view_model.py` |
| 31 | Add `ProjectStateViewModel.current_page` public accessor; eliminate `._project_state` accesses in `page_view.py` and `project_view.py` | architecture.md A2 | `project_state_view_model.py`, `page_view.py`, `project_view.py` |
| 32 | Merge `_action_context` into a shared base or utility; eliminate duplication between `ProjectView` and `PageView` | architecture.md A6 | `project_view.py`, `page_view.py` |
| 33 | Merge `_reload_ocr_async` and `_reload_ocr_edited_async` | architecture.md A6 | `views/projects/pages/page_view.py` |
| 34 | Merge `_emit_word_rebox_bbox`, `_emit_word_add_bbox`, `_emit_erase_bbox` into a single `_emit_scaled_rect` helper | architecture.md A6 | `views/projects/pages/image_tabs.py` |
| 35 | Document and deduplicate `asyncio.sleep(0.1)` pattern across 14 call sites | architecture.md A6 | `project_view.py`, `page_view.py` |
| 36 | Extract filesystem browser from `ProjectLoadControls` into a service | architecture.md A10 | `views/header/project_load_controls.py` |
| 37 | Move `_build_word_match_page_key` from `TextTabs` to `WordMatchViewModel` or a utility module | architecture.md A3 | `views/projects/pages/text_tabs.py` |
| 38 | Break `TextTabs.__init__` (300 lines) into `_build_word_callbacks`, `_build_line_callbacks`, `_build_paragraph_callbacks` | architecture.md A3 | `views/projects/pages/text_tabs.py` |
| 39 | Fix `project_operations.reload_ground_truth_into_project` — return data; let the caller (state layer) apply it | architecture.md A8 | `operations/persistence/project_operations.py` |
| 40 | Replace hand-rolled YAML parser in `config_operations.py` with `yaml.safe_load` | architecture.md + bugs.md | `operations/persistence/config_operations.py` |
| 41 | Split `page_operations.py` (~1,800 lines) into `predictor_operations.py`, `page_io_operations.py`, `provenance_operations.py` | architecture.md A12 | `operations/ocr/page_operations.py` |
| 42 | Split `page_state.py` (~2,650 lines): extract dispatch + structural ops, text cache, overlay management, validation snapshot | architecture.md A1 | `state/page_state.py` |
| 43 | Centralise provenance storage on `PageModel.saved_provenance` only; remove triple-store | architecture.md A7 | `operations/ocr/page_operations.py` |
| 44 | Replace `_image_mappings()` loop abstraction in `PageStateViewModel` with direct call | architecture.md A6 | `viewmodels/project/page_state_view_model.py` |
| 45 | Unify `_update_image_sources_async` / `_update_image_sources_blocking` into a shared `_build_encoded_results` helper | architecture.md A6 | `viewmodels/project/page_state_view_model.py` |

---

## Notes for Opus

- Before starting any tier-4 refactor, run the full test suite and confirm it
  passes as a baseline.
- For each tier-4 item, write or update tests before making structural changes.
- Items 28–31 (public API exposure + private-access elimination) are best done
  together in one pass since they touch overlapping files.
- The `TextTabs` refactoring (37–38) will likely surface the listener
  ordering dependency (correctness depends on which `on_change` handler fires
  first). Document that dependency explicitly as you go, even if not fixing it
  immediately.
- `page_state.py` (item 42) is the highest-risk split. Do it last, after all
  other state-layer bugs are fixed, and test exhaustively.
