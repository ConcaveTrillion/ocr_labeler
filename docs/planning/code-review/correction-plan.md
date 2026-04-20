# Correction Plan

Prioritized implementation plan for code review findings. Grouped into
phases, ordered by impact and risk.

**Status**: Phases 1–3.7, 5.1–5.7, 2.1–2.8, and 6.1 completed.
Phase 3.2/3.3 (presentation strings moved to viewmodel),
Phase 3.4 (image cache extraction to operations),
Phase 3.5 (match-status classification extracted to operations),
Phase 6.0 (Page metadata), and crop_image delegation done.
Phase 4.2 (page_state dispatch helper — 28 methods consolidated;
follow-up: unused `page_index` removed from 34 PageState methods
and all callers in text_tabs.py, test files, and image_tabs.py),
Phase 4.3 (word_edit_dialog converted from closure function to class;
follow-up: `open_word_edit_dialog()` wrapper removed),
Phase 4.5 (text_tabs callback factory — 24 closures replaced),
Phase 4.6 (BaseView teardown lifecycle added).
Phase 4.1 (split LineOperations 4048→1823 lines via mixin pattern),
Phase 4.4 (word_match delegation — 80 wrappers removed, 1448→834 lines).
Remaining: 6.2–6.4 (pd-book-tools structural migration).
All 715 ocr-labeler tests and 491 pd-book-tools tests pass.

## Phase 1: Bug Fixes and Quick Wins

Low-risk changes that fix correctness issues and eliminate trivially
duplicated code.

### 1.1 Fix `dict[str, any]` bug

- **File**: `line_operations.py` L438
- **Fix**: Change `any` → `Any` (import from typing)
- **Risk**: None
- **Effort**: Trivial

### 1.2 Fix `_word_style_signature` ignoring `right_footnote`

- **File**: `text_tabs.py` ~L1311
- **Fix**: Add `right_footnote` to the signature key
- **Risk**: None
- **Effort**: Trivial

### 1.3 Centralize `WORD_LABEL_*` constants

- **Create**: `ocr_labeler/models/constants.py`
- **Move**: All `WORD_LABEL_*` constants from `word_match.py`,
  `word_match_gt_editing.py`, `page_operations.py`
- **Also move**: `WordKey` and `ClickEvent` type aliases
- **Update**: All imports
- **Risk**: Low (import changes only)
- **Effort**: Small

### 1.4 Consolidate `IMAGE_EXTS` constant

- **Add**: To `models/constants.py`
- **Replace**: All inline `{".png", ".jpg", ".jpeg"}` sets
- **Risk**: Low
- **Effort**: Trivial

### 1.5 Remove dead code

- Delete `services/notification_service.py` (unused)
- Delete `_resolve_text` and `_resolve_bbox` from `doctr_export.py`
- Remove unused `train_val_split` parameter from
  `DocTRExportOperations.__init__`
- Remove unused logger from `project_model.py`
- **Risk**: Low
- **Effort**: Small

### 1.6 Fix false async in `OCRService`

- **File**: `ocr_service.py`
- **Fix**: Remove `async` from methods with no `await`
- **Risk**: Low (check all callers)
- **Effort**: Small

### 1.7 Standardize logger import and severity

- Replace `__import__("logging")` pattern with standard `import logging`
  in `base_viewmodel.py` and `base_view.py`
- Change `logger.critical` → `logger.warning` in `project_state.py`
  guard conditions
- Change `logger.warning` → `logger.debug` for boundary conditions in
  `navigation_operations.py`
- **Risk**: None
- **Effort**: Trivial

## Phase 2: Deduplication

Consolidate duplicated implementations without changing architecture.

### 2.1 Extract shared `get_cropped_image` utility

- **Create**: `ocr_labeler/operations/ocr/image_utils.py`
- **Extract**: Common crop pipeline from `word_match_model.py` and
  `line_match_model.py`
- **Both models**: Call the shared utility
- **Risk**: Low
- **Effort**: Small

### 2.2 Unify `_element_bbox` in `image_tabs.py`

- **Replace**: `_word_bbox`, `_line_bbox`, `_paragraph_bbox` with single
  `_element_bbox(element, page)`
- **Risk**: Low
- **Effort**: Small

### 2.3 Create selection snapshot context manager

- **File**: `word_match_actions.py`
- **Create**: `_with_selection_snapshot()` context manager or helper
- **Replace**: ~25 repetitions of save/clear/restore pattern
- **Risk**: Medium (many call sites)
- **Effort**: Medium

### 2.4 Extract `_resolve_workspace_save_directory` to shared location

- **From**: `page_state.py` and `project_state.py`
- **To**: `operations/persistence/persistence_paths_operations.py`
- **Risk**: Low
- **Effort**: Small

### 2.5 Consolidate `queue_notification` / `pop_notification`

- **Extract**: Notification queue to a shared mixin or base class
- **Apply to**: `app_state.py` and `project_state.py`
- **Risk**: Low
- **Effort**: Small

### 2.6 Consolidate `_notify` / `_notify_once` in views

- **Move**: To `BaseView` or a `NotificationMixin`
- **Update**: `project_load_controls.py`,
  `project_navigation_controls.py`, `project_view.py`,
  `page_actions.py`, `image_tabs.py`
- **Risk**: Low
- **Effort**: Small

### 2.7 Extract `_bind_from_safe` / `_bind_disabled_from_safe`

- **From**: `project_load_controls.py`,
  `project_navigation_controls.py`
- **To**: `views/shared/` utility
- **Risk**: Low
- **Effort**: Trivial

### 2.8 Consolidate `_is_geometry_normalization_error`

- **From**: `line_operations.py`, `page_operations.py`
- **To**: One canonical location, other imports
- **Risk**: Low
- **Effort**: Trivial

## Phase 3: Layer Corrections

Move code between layers to fix MVVM violations and improve separation
of concerns.

### 3.1 Add public notification methods to `AppStateViewModel`

- **Add**: `queue_notification()`, `pop_notification()` as public
  methods
- **Update**: All 5 view files that reach through privates
- **Risk**: Low
- **Effort**: Small

### 3.2 Move presentation strings out of state

- **Extract**: `current_page_source_text`, `current_page_source_tooltip`,
  `current_page_export_status` from `page_state.py`
- **To**: `page_state_view_model.py` (or introduce status enums in state
  that viewmodel maps to display strings)
- **Risk**: Medium (many consumers)
- **Effort**: Medium

### 3.3 Move `get_page_source_text` out of `text_operations.py`

- Return an enum/status code from operations
- Map to display strings in viewmodel
- **Risk**: Low
- **Effort**: Small

### 3.4 Extract image caching from `page_state_view_model.py`

- **Create**: `operations/ocr/image_cache_operations.py`
- **Move**: ~300 lines of cv2 resize/encode/write logic
- **ViewModel**: Calls operations, manages only view state
- **Risk**: Medium
- **Effort**: Medium-Large

### 3.5 Move match-status classification to operations

- **From**: `word_match_renderer.py` `apply_local_word_gt_update` and
  `word_match_view_model.py` `_create_word_match`
- **To**: New or existing operations module
- **Risk**: Medium
- **Effort**: Medium

### 3.6 Move `clear_scope_on_word` logic to operations

- **From**: `views/projects/pages/word_operations.py` L210-252
- **To**: `operations/ocr/word_operations.py`
- View calls operations method instead of mutating model directly
- **Risk**: Low
- **Effort**: Small

### 3.7 Fix views/state `__init__.py` re-exports

- Remove `PageOperations` and `ProjectOperations` re-exports from
  `state/__init__.py`
- **Risk**: Low (check all imports)
- **Effort**: Trivial

## Phase 4: Structural Improvements

Larger refactoring to address god objects and file size issues.

### 4.1 Split `LineOperations` (4040 lines)

- **Into**:
  - `line_operations.py` — line-level merge/delete/split (1823 lines)
  - `paragraph_operations.py` — paragraph-level operations (mixin)
  - `word_bbox_operations.py` — bbox refinement/expansion (mixin)
  - `page_structure_operations.py` — page-wide helpers (base class)
    (recompute bboxes, prune empty, find parent)
- **Risk**: High (many callers in page_state.py)
- **Effort**: Large
- **Status**: Done — Extracted ~2225 lines into 3 new modules using
  mixin inheritance pattern. `LineOperations` inherits from
  `PageStructureOperations`, `ParagraphOperationsMixin`, and
  `WordBboxOperationsMixin`. All public API unchanged (MRO provides
  all methods). No changes needed to `page_state.py` dispatch.

### 4.2 Reduce `page_state.py` boilerplate (2586 lines)

- **Create**: Generic dispatch helper for the 25+ identical
  structural editing methods
- **Each method**: Becomes a 3-line call to the dispatcher
- **Risk**: Medium
- **Effort**: Medium
- **Status**: Done — `_dispatch_line_op()` consolidates 28 methods.
- **Follow-up**: Done — Removed unused `page_index` parameter from 34
  `PageState` methods (28 dispatch + 6 word methods). Updated all
  callers in `text_tabs.py` (`_make_page_callback` factory),
  `word_edit_dialog.py`, `word_match_renderer.py`, and all test files.

### 4.3 Decompose `open_word_edit_dialog` (1190 lines)

- **File**: `word_edit_dialog.py`
- **Convert**: From single function with 20 closures to a class with
  methods
- **Risk**: Medium-High (complex closure state)
- **Effort**: Large
- **Status**: Done — `WordEditDialog` class created, thin
  `open_word_edit_dialog()` wrapper retained for compatibility.
- **Follow-up**: Done — Removed `open_word_edit_dialog()` wrapper.
  Callers (`word_match_renderer.py`, `_rerender_dialog`) now
  instantiate `WordEditDialog(view, ...).open()` directly.

### 4.4 Reduce delegation boilerplate in `word_match.py`

- Remove 30+ pure delegation methods
- Renderer and toolbar call `self._view.actions.*` directly
- **Risk**: Medium
- **Effort**: Medium
- **Status**: Done — Removed ~80 pure delegation methods (1448→834 lines).
  Updated callers in content.py, text_tabs.py, word_edit_dialog.py,
  and test_word_match.py to access sub-components directly
  (`.actions.*`, `.selection.*`, `.bbox.*`, `.gt_editing.*`,
  `.renderer.*`, `.toolbar.*`).

### 4.5 Refactor `text_tabs.py` callback closures

- Create a callback builder helper
- Replace 35+ closures in `__init__` with factory calls
- **Risk**: Medium
- **Effort**: Medium

### 4.6 Add `BaseView.teardown()` lifecycle

- **File**: `base_view.py`
- **Add**: Listener cleanup on view disposal
- **Ensure**: All views that register listeners clean up
- **Risk**: Medium (need to identify all registration points)
- **Effort**: Medium

## Phase 5: Style Normalization

Low-risk but low-impact style consistency improvements.

### 5.1 Normalize `Optional[X]` → `X | None`

- All files already have `from __future__ import annotations`
- Bulk find-and-replace `Optional[X]` → `X | None`
- Remove `from typing import Optional` where no longer needed
- **Risk**: None
- **Effort**: Small

### 5.2 Normalize collection type annotations

- `List[X]` → `list[X]`, `Dict[X, Y]` → `dict[X, Y]`,
  `Tuple[X, Y]` → `tuple[X, Y]`
- **Risk**: None
- **Effort**: Small

### 5.3 Fix f-string logging

- Replace `logger.info(f"...")` with `logger.info("...", arg)` in 20+
  locations
- Replace `logger.exception(f"Error: {e}")` with
  `logger.exception("Error description")`
- **Risk**: None
- **Effort**: Small-Medium

### 5.4 Standardize `notify()` error handling

- Add per-listener try/except to `AppState.notify()` and
  `ProjectState.notify()` to match `PageState.notify()`
- **Risk**: Low
- **Effort**: Trivial

### 5.5 Make `page_count()` a property

- **File**: `project_model.py`
- **Risk**: Low (check all callers using `()`)
- **Effort**: Trivial

### 5.6 Fix `_page_index` ad-hoc attribute

- **File**: `page_state.py`
- Declare `_page_index: int = field(default=0, init=False)` on the
  dataclass
- **Risk**: Low
- **Effort**: Trivial

### 5.7 Standardize static vs instance methods

- Convert `ProjectOperations` methods to `@staticmethod`/`@classmethod`
  where no instance state is used
- **Risk**: Low
- **Effort**: Small

## Phase 6: pd-book-tools Migration (Long-Term)

See [pd-book-tools-candidates.md](pd-book-tools-candidates.md) for
details. These require changes to the external library.

### 6.1 Add `BoundingBox.crop(image)` to pd-book-tools

### 6.2 Move structural operations to pd-book-tools

**DONE** — Created `pd_book_tools.ocr.page_structure_operations` (PageStructureOperations),
`pd_book_tools.ocr.paragraph_operations` (ParagraphOperationsMixin), and
`pd_book_tools.ocr.word_bbox_operations` (WordBboxOperationsMixin).
ocr-labeler files replaced with thin re-export wrappers.

### 6.3 Move geometry helpers to pd-book-tools

**DONE** — Added `vertical_midpoint`, `horizontal_midpoint`, and `y_range`
properties to `BoundingBox`. Geometry helpers in `PageStructureOperations`
use these directly.

### 6.4 Standardize Word style API in pd-book-tools

**DONE** — Created `pd_book_tools.ocr.word_style_operations` (WordStyleOperations)
with style read/write/apply/remove methods. ocr-labeler's `WordOperations` now
extends `WordStyleOperations` and adds only `classify_match_status` (which
depends on the ocr-labeler `MatchStatus` enum).

## Summary

| Phase | Items | Estimated Scope | Risk |
| --- | --- | --- | --- |
| 1: Bug Fixes | 7 | Small | Low |
| 2: Deduplication | 8 | Medium | Low-Medium |
| 3: Layer Corrections | 7 | Medium-Large | Medium |
| 4: Structural | 6 | Large | Medium-High |
| 5: Style | 7 | Small-Medium | Low |
| 6: pd-book-tools | 4 | Large | High |
