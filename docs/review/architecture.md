# Architectural and Structural Issues

---

## A1 — God-class file sizes

The following files are too large to maintain and should be split.

| File | Lines | Suggested split |
|---|---|---|
| `state/page_state.py` | ~2,650 | Dispatch helpers + structural ops; text cache; overlay management; validation snapshot |
| `state/project_state.py` | ~1,764 | Page load lifecycle; GT management; navigation; export |
| `operations/ocr/page_operations.py` | ~1,800 | `predictor_operations.py`; `page_io_operations.py`; `provenance_operations.py` |
| `viewmodels/project/page_state_view_model.py` | ~1,003 | Image encode/cache module; state sync module |
| `views/projects/pages/text_tabs.py` | ~950 | Constructor wiring (~300 lines); fingerprinting logic (85 lines) |
| `views/projects/pages/image_tabs.py` | ~1,101 | `DragHandler`; `OverlayRenderer`; `SelectionTracker` |

---

## A2 — MVVM boundary violations (14+ sites)

Views and viewmodels directly access private attributes of other layers.
All of these should be replaced with public properties or methods.

| Location | Violation |
|---|---|
| `views/projects/pages/content.py:26` | `page_state_view_model._page_state` |
| `views/projects/pages/image_tabs.py` (8+ sites) | `getattr(page_state_view_model, "_page_state", None)` |
| `views/projects/pages/page_view.py:30,113,380,432` | `project_view_model._project_state` |
| `views/projects/pages/page_view.py:200–201` | `_app_state_model._app_state.queue_notification` |
| `views/projects/project_view.py:340` | `self.viewmodel._project_state` |
| `views/projects/pages/text_tabs.py:412–413` | `page_state._project_state` |
| `views/main_view.py:132–145` | `project_view._root` |
| `viewmodels/main_view_model.py:79–115` | Writes `project_state_view_model._project_state`; calls `._on_project_state_change` |
| `viewmodels/project/project_state_view_model.py:71` | `_app_state_model._app_state.on_change` |

**Fix:** Expose `current_page`, `project_root`, `rebind(new_state)` as public APIs on
the relevant viewmodels. Views should never reach through `_` attributes.

---

## A3 — `TextTabs` bypasses the viewmodel entirely

**File:** `views/projects/pages/text_tabs.py`

`TextTabs` accepts a raw `PageState` domain object and wires 30+ callbacks directly
to domain-layer methods. `PageStateViewModel` exists but `TextTabs` does not use it.

The constructor (~300 lines) should be broken into:
- `_build_word_callbacks()`
- `_build_line_callbacks()`
- `_build_paragraph_callbacks()`

The SHA1 fingerprinting method `_build_word_match_page_key` (85 lines) is business
logic inside a view class; it belongs in a utility module or in `WordMatchViewModel`.

---

## A4 — Listener lifecycle is not managed

All viewmodels and `TextTabs` register on state `on_change` lists but never
unregister. `BaseView.teardown()` exists but is never called from the session
disconnect handler. In a multi-session or long-running server:

- Old `ProjectState` listeners fire after the project is unloaded, causing
  phantom refreshes.
- `WeakRef`-based or explicit teardown is needed at session disconnect.

**Affected files:** All viewmodels, `TextTabs`, `BaseView` subclasses.

---

## A5 — Dual pub-sub systems without unification

NiceGUI's `@binding.bindable_dataclass` property-change events coexist with
the manual `_property_changed_callbacks` list on `BaseViewModel`. The manual
system is needed only for cross-VM coordination (e.g., `MainViewModel` watching
`AppStateViewModel`), but it requires:

1. A maintained whitelist of property names in `AppStateViewModel.__setattr__`
2. Manual `notify_property_changed(name, value)` calls at every assignment
3. Each new property must be added to both the class declaration and the whitelist

Forgetting the whitelist update is a silent correctness bug. Consider replacing
the manual system with a structured event enum or making the cross-VM
coordination reactive via direct bindings.

---

## A6 — Duplicated constants and logic

### Image extension set defined in four places

`{".png", ".jpg", ".jpeg"}` appears as a literal in:
- `operations/persistence/project_operations.py`
- `operations/persistence/project_discovery_operations.py`
- `operations/ocr/page_operations.py`
- `operations/export/doctr_export.py`

`IMAGE_EXTS` in `constants.py` already exists. All four literals should import
and use it.

### Other duplications

| Duplicated item | Locations |
|---|---|
| `_reorganize_page_if_available` | `ocr_service.py` (getattr) and `page_operations.py` (Protocol) |
| `_is_envelope` / `is_user_page_envelope` | `doctr_export.py` private fn vs `models` public fn |
| `_resolve_workspace_save_directory` | Both `ProjectState` and `PageState` thin wrappers |
| `_action_context` async context manager | `ProjectView` and `PageView` (identical copies) |
| `_reload_ocr_async` / `_reload_ocr_edited_async` | ~60 lines differing only in `use_edited_image=True/False` |
| `_emit_word_rebox_bbox/add/erase` | 90%+ identical in `image_tabs.py` |
| Drag state machine | `_handle_drag_mouse`, `_handle_word_rebox_drag`, `_handle_erase_drag` — triplicated |
| `asyncio.sleep(0.1)` | 14 occurrences across `ProjectView` and `PageView`, never documented |

---

## A7 — Provenance triple-storage design

**File:** `operations/ocr/page_operations.py:_store_saved_provenance` ~lines 1592–1603

Every page save stores the same provenance dict in three places:
1. `page_model.saved_provenance`
2. `_saved_provenance_by_page_id[id(page_model)]`
3. `setattr(page_obj, PAGE_SAVED_PROVENANCE_ATTR, ...)`

`_resolve_saved_provenance` then has a five-tier lookup cascade. The complexity
exists because the dict grows without bound (see ML1 in bugs.md). The design
should be centralised on `PageModel.saved_provenance` alone, with `_saved_provenance_by_page_id`
replaced by a `WeakKeyDictionary`.

---

## A8 — Wrong-layer concerns

Several items belong in a different layer:

| Item | Current location | Should be in |
|---|---|---|
| `get_page_source_text` returning UI display strings | `operations/ocr/text_operations.py` | ViewModel or view |
| `schedule_navigation` orchestrating callbacks | `operations/ocr/navigation_operations.py` | ViewModel |
| `reload_ground_truth_into_project` accepting `AppState` | `operations/persistence/project_operations.py` | State layer |
| `_build_word_match_page_key` (SHA1 fingerprint) | `views/projects/pages/text_tabs.py` | Utility module or ViewModel |
| Directory browser + `mkdir` | `views/header/project_load_controls.py` | Service or Operation |
| Blocking `load_all_saved_pages()` called in async handler | `views/projects/pages/export_dialog.py` | Should use `run.io_bound` |

---

## A9 — `notify()` thread-safety

`PageState.notify()` and `ProjectState.notify()` can be called from worker
threads (the `run.io_bound` thread pool that runs `ensure_page_model` /
`_navigate`). Their listeners may call `ui.*` methods that require the NiceGUI
asyncio event loop context. NiceGUI provides `ui.run_javascript` and related
facilities that are safe to call from threads — direct `ui.*` calls are not.

All listener callbacks that touch NiceGUI UI state should be dispatched via
`background_tasks.create()` or `run_safe()` to ensure they run on the event loop.

---

## A10 — `ProjectLoadControls` embeds a filesystem browser

**File:** `views/header/project_load_controls.py` ~lines 241–388

~150 lines of directory traversal, path resolution, and breadcrumb construction
live inside a view class. The file also calls `candidate.mkdir(parents=True, exist_ok=True)`
in an event handler — a side-effecting disk operation in the view layer.

**Fix:** Extract to a `FilesystemBrowserService` or a utility module in `operations/persistence/`.

---

## A11 — `set_action_busy` interleaving between `ProjectView` and `PageView`

**Files:** `views/projects/project_view.py`, `views/projects/pages/page_view.py`

Both `ProjectView` and `PageView` call `set_action_busy(True/False)` on the same
`ProjectStateViewModel`. If a navigation action starts while a save is in progress,
the two `False` calls can arrive in either order, leaving the busy overlay
permanently shown or prematurely cleared.

**Fix:** Use a reference-counted busy flag or a flag per operation type.

---

## A12 — `page_operations.py` acts as a god class

`page_operations.py` (~1,800 lines) manages: predictor lifecycle, OCR-from-scratch,
save/load with the `UserPageEnvelope` schema, bbox refinement, image loading,
provenance tracking, and cached image cleanup.

Suggested split:
- `predictor_operations.py` — predictor lifecycle, HF weight resolution
- `page_io_operations.py` — save, load, envelope handling, cache image management
- `provenance_operations.py` — all provenance assembly, resolution, and storage

The `_resolve_ocr_provenance_for_save` method alone is a 5-tier cascade that
silences exceptions internally at four levels. Isolating it in `provenance_operations.py`
would make it far easier to test and reason about.
