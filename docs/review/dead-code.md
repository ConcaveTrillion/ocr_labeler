# Dead Code

These modules, classes, and symbols are unused in the application and should be removed
or explicitly deprecated. Removing them reduces confusion for future contributors and
removes the false impression that these are available APIs.

---

## D1 — `OCRService` and `OCREngine` in `operations/ocr/ocr_service.py`

**Status:** Never instantiated in the application. All actual OCR runs through
`PageOperations._get_or_create_predictor()`. `OCRService` is re-exported from
`operations/__init__.py`, giving the false impression it is a supported API.

**Additional problems in this file:**
- `async def` methods that contain no `await` — they block the event loop
- Duplicates `_reorganize_page_if_available` from `page_operations.py` (using
  `getattr` instead of a `Protocol`)
- `get_supported_formats` claims `tiff`/`bmp` support that the rest of the app
  never provides
- `process_page` monkey-patches attributes directly onto `Page` objects,
  inconsistent with `PageModel`

**Action:** Delete `operations/ocr/ocr_service.py`. Remove re-export from
`operations/__init__.py`.

---

## D2 — `NotificationService` in `services/notification_service.py`

**Status:** Zero imports outside of `services/__init__.py` itself. All
notifications in the application go through `AppState.queue_notification()` /
`pop_notification()` drain in the view, or directly via `ui.notify`.

**Additional problems:**
- `info` method omits `type=` arg, inconsistent with other severity methods
- `error` and `warning` methods log at the corresponding log level for every
  display notification — would make every user-facing warning an `ERROR` log
- Has an unimplemented `# TODO: Wire disable/enable to a UI toggle` comment

**Action:** Delete `services/notification_service.py`. Remove re-export from
`services/__init__.py`.

---

## D3 — `NavigationOperations.schedule_navigation`

**File:** `pd_ocr_labeler/operations/ocr/navigation_operations.py` ~lines 153–180  
**Status:** Never called in the application. Only exercised in its own unit test.
The application uses only the four pure-computation methods
(`next_page`, `prev_page`, `goto_page_number`, `goto_page_index`).

**Additional problem:** The method is synchronous but claims to support async
use. Its docstring says "caller is responsible for running in an async context"
but it makes no attempt to be non-blocking.

**Action:** Delete `schedule_navigation` and its test. If the pattern is ever
needed, it should be re-implemented as a proper async method.

---

## D4 — `operations/validation/` package

**Status:** The package contains only `__init__.py` with `__all__ = []` and a
placeholder comment. No validation operations have been implemented. The
`operations/__init__.py` does not import from it.

**Action:** Delete the `operations/validation/` directory, or if it is a
placeholder for planned work, add a docstring explaining what belongs here.

---

## D5 — `word_operations.py` re-exported constants

**File:** `pd_ocr_labeler/operations/ocr/word_operations.py` ~lines 16–17  
**Status:** `STYLE_LABEL_BY_ATTR` and `WORD_COMPONENT_BY_ATTR` are defined as
module-level names but have zero callers outside this file.

**Action:** Remove the two re-export lines.

---

## D6 — `ProjectStateViewModel.can_navigate_override`

**File:** `pd_ocr_labeler/viewmodels/project/project_state_view_model.py` ~line 36  
**Status:** Declared as `can_navigate_override: bool = False` and referenced in
`_update_navigation_properties`. Never set to `True` anywhere in the codebase.

**Action:** Remove the field and the branch in `_update_navigation_properties`
that reads it.

---

## D7 — Query methods prefixed `command_` on `MainViewModel` and `ProjectStateViewModel`

**Files:** `viewmodels/main_view_model.py`, `viewmodels/project/project_state_view_model.py`  
**Status:** `command_get_project_display_name`, `command_get_navigation_status`,
`command_get_page_display_info` are pure read-only queries with a `command_`
prefix. None appear to be called from any view. They also violate Command-Query
Separation naming convention.

**Action:** Verify with `grep` that there are no callers, then delete them.

---

## D8 — `TextTabsModel.__setattr__` commented-out override

**File:** `pd_ocr_labeler/views/projects/pages/text_tabs.py` ~lines 46–56  
**Status:** Commented-out method body that was intended to propagate model
changes back to `PageState`. The comment is dead and the approach was abandoned.

**Action:** Delete the commented-out block.

---

## D9 — `AppState.__post_init__` marked `# pragma: no cover`

**File:** `pd_ocr_labeler/state/app_state.py` ~line 127  
**Status:** `# pragma: no cover - simple initialization` is applied to one of the
most important methods in the class (populates `available_projects`,
`project_keys`, and initial model selection).

**Action:** Remove the pragma. Add tests for the initialization paths it skips.

---

## D10 — `view_helpers.py:_notified_error_keys` lazy init pattern

**File:** `pd_ocr_labeler/views/shared/view_helpers.py` ~line 23  
**Status:** `_notified_error_keys: set[str]` is declared as a class-level
annotation with no default, relying on `_ensure_notified_keys()` for lazy init.
The lazy init only exists because `NotificationMixin` has no `__init__`. The
field should have a proper `field(default_factory=set)` declaration.

**Action:** Add `field(default_factory=set)` or convert to a proper dataclass field.
