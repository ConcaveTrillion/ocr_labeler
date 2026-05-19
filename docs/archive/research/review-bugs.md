# Bugs

## Critical — Crash or Always-Wrong Behaviour

### B1 — `can_load_page` exception handler crashes on `save_directory=None`

**File:** `pd_ocr_labeler/operations/ocr/page_operations.py` ~lines 957–972
**Severity:** Crash
**Description:**
The `except` handler calls `Path(save_directory)` without checking whether
`save_directory` is `None` (its default). `Path(None)` raises `TypeError`,
replacing the original exception with a new crash. The intended fallback path
is never reached.
**Fix:** Replace `Path(save_directory)` with `_resolve_save_directory(project_root, save_directory)`.

---

### B2 — Repeating session-init timer (no `once=True`)

**File:** `pd_ocr_labeler/app.py` ~line 277
**Severity:** Repeated unwanted callbacks
**Description:**
`ui.timer(0.05, start_url_initialization)` fires every 50 ms indefinitely.
`url_init_started` prevents double-loading, but the timer accumulates in memory
and its tick overhead is unnecessary.
**Fix:** Pass `once=True` to `ui.timer`.

---

### B3 — Cross-session log contamination via O(N²) handler proliferation

**File:** `pd_ocr_labeler/app.py:_setup_session_logging` ~lines 148–157
**Severity:** Data integrity (log files)
**Description:**
Every new browser tab appends its `FileHandler` to **all** existing loggers
that have `propagate=False`. With N tabs open, tab N's handler is added to N-1
prior loggers. Session log files contain records from other sessions.
**Fix:** Attach the handler only to the session-specific logger, not to all
loggers.

---

### B4 — Export staleness check always reports "not exported"

**File:** `pd_ocr_labeler/operations/export/doctr_export.py:check_page_export_status` ~line 241
**Severity:** Always-wrong result
**Description:**
`check_page_export_status` looks for `{project_id}_{page_index}.png`
(e.g. `myproject_0.png`). The actual export path produced by `_run_export`
uses `{json_path.stem}_{page.page_index}.png`
(e.g. `myproject_001_0.png`). The two naming conventions do not match.
Every page is always reported as unexported regardless of actual state.
**Fix:** Align the path construction in `check_page_export_status` with
the actual path written by `_run_export`.

---

### B5 — Partial page mutation on bbox validation failure

**File:** `pd_ocr_labeler/operations/ocr/bbox_operations.py:_apply_to_word_keys` and `_apply_to_line_indices`
**Severity:** Silent data corruption
**Description:**
Both methods iterate over a selection and return `False` immediately on a bad
key. Mutations already applied to earlier entries in the loop are **not**
reverted. The page is left half-modified with no recompute triggered.
Callers that check the `False` return will think nothing changed; the page
actually has partial changes.
**Fix:** Validate all keys up front before applying any mutations, or collect
changes and apply atomically.

---

### B6 — Navigation-derived properties never update (`show_project_view`, `show_placeholder`)

**File:** `pd_ocr_labeler/viewmodels/project/project_state_view_model.py:_on_project_state_change`
**Severity:** UI never updates on navigation
**Description:**
`_on_project_state_change` fires `notify_property_changed("project_state", ...)`.
`MainViewModel._on_project_state_changed` only responds to the names
`"page_total"` and `"current_page_index"`. The generic sentinel `"project_state"`
never matches, so `_update_derived_properties` is never triggered by navigation
changes. `show_project_view` and `show_placeholder` remain stale.
**Fix:** Fire `notify_property_changed("page_total", ...)` and
`notify_property_changed("current_page_index", ...)` when those values change,
or update the listener in `MainViewModel` to react to `"project_state"`.

---

## Memory Leaks

### ML1 — `_saved_provenance_by_page_id` grows without bound

**File:** `pd_ocr_labeler/operations/ocr/page_operations.py` ~lines 114, 1598–1599
**Description:**
The dict maps `id(page_model)` and `id(page_obj)` to provenance dicts.
Python reuses `id()` values after GC, so stale entries accumulate across the
session lifetime with no eviction.
**Fix:** Replace with `weakref.WeakKeyDictionary`.

---

### ML2 — State listeners never removed; stale callbacks accumulate

**Files:** `viewmodels/app/app_state_view_model.py`,
`viewmodels/project/project_state_view_model.py`, `views/projects/pages/text_tabs.py`
**Description:**
All three register callbacks on `AppState.on_change`, `ProjectState.on_change`,
and `PageState.on_change` at construction time. `BaseView.teardown()` exists
but is never called anywhere in the codebase. Across project switches, old
listeners remain registered, causing phantom refreshes and accumulating objects
in memory.
**Fix:** Call `BaseView.teardown()` on session disconnect. Add a corresponding
`BaseViewModel.teardown()` that removes listeners from state `on_change` lists.

---

## Correctness Bugs

### C1 — `load_page_model` double-parses `UserPageEnvelope`

**File:** `pd_ocr_labeler/operations/ocr/page_operations.py` ~lines 637–641 and 716–720
**Description:**
`UserPageEnvelope.from_dict(json_data)` is called twice on the same data:
once to apply word attributes, and again later to retrieve `original_page_dict`
and `cached_images`. Every page load pays double deserialization.
**Fix:** Parse once at line ~637 and pass the result to both consumers.

---

### C2 — `image_path` variable shadowed from `Path` to `str` in `load_page_model`

**File:** `pd_ocr_labeler/operations/ocr/page_operations.py` ~lines 656–708
**Description:**
`image_path` is first bound to a `Path | None` (the found image file at ~line
660), then rebound to a `str | None` from the JSON source dict at ~line 698.
Code after line 698 that expects a `Path` receives a `str`. No runtime error
fires immediately, but downstream callers calling `.suffix` or `.parent` on it
will fail.
**Fix:** Use distinct variable names (`image_path_for_read` vs `image_path_str`).

---

### C3 — `_update_text_cache` fires `notify()` from a property getter

**File:** `pd_ocr_labeler/state/page_state.py` ~line 2638
**Description:**
`_update_text_cache` unconditionally calls `self.notify()` after updating the
cache. Any NiceGUI binding that reads `current_ocr_text` or `current_gt_text`
triggers a full listener chain and potentially a DOM repaint cycle. Property
accessors must not have notification side effects.
**Fix:** Remove the `notify()` call from `_update_text_cache`; call `notify()`
explicitly at the call site when a page navigation occurs instead.

---

### C4 — `@notify_on_completion` triple-fires `notify()` on structural edits

**File:** `pd_ocr_labeler/state/page_state.py`
**Description:**
`_finalize_structural_edit` → `_auto_save_to_cache()` → `persist_page_to_file`
(decorated `@notify_on_completion`, fires `notify()`) → decorator fires
`notify()` again → `_finalize_structural_edit` also calls `self.notify()`.
Every structural edit produces at least 3 `notify()` calls.
**Fix:** Either remove `@notify_on_completion` from methods that call
`notify()` internally, or consolidate notification to a single point at the
top of each user-visible operation.

---

### C5 — Hardcoded dev path as `project_root` default

**File:** `pd_ocr_labeler/state/project_state.py:69`
**Description:**
`project_root: Path = Path("../data/source-pgdp-data/output")` leaks an
internal dev directory into the production dataclass. All `.name` accesses
on this path (lines 1190, 1328, 1349, 1419, 1424) resolve against the wrong
directory if the field is ever left at default.
**Fix:** Change the default to `field(default=None)` and type it as
`Path | None`; add null guards on every `.name` access.

---

### C6 — `build_project_url` produces malformed URLs for non-ASCII project names

**File:** `pd_ocr_labeler/routing.py:build_project_url`
**Description:**
Project keys with spaces or non-ASCII characters are interpolated directly
into the URL string with no percent-encoding. The resulting URL is malformed
and will fail to route correctly.
**Fix:** Apply `urllib.parse.quote(project_key, safe="")` before interpolation.

---

### C7 — `pick_default_keys` unreachable branch produces wrong fallback

**File:** `pd_ocr_labeler/operations/ocr/model_selection_operations.py` ~line 480
**Description:**
The final `if hf_available:` block with reason `"hf-only"` is unreachable.
The prior conditional structure ensures all `hf_available=True` cases are
handled before reaching it. The dead branch is evidence of incomplete reasoning
about the priority rules, which may mean an actual edge case (HF only, no
local models) silently falls through without a proper default.
**Fix:** Trace all possible paths through `pick_default_keys` and add a test
for the HF-only case.

---

### C8 — `model_selection_operations` makes blocking network calls at startup

**File:** `pd_ocr_labeler/operations/ocr/model_selection_operations.py:discover_model_options` ~lines 350, 364
**Description:**
Two sequential `fetch_hf_last_modified` calls (5-second timeout each) are made
synchronously at startup inside `discover_model_options`. This blocks the
NiceGUI asyncio event loop for up to 10 seconds on startup.
**Fix:** Run both calls in `run.io_bound()` or in a startup background task.

---

### C9 — `app_state.py:is_loading.setter` does not call `notify()`

**File:** `pd_ocr_labeler/state/app_state.py` ~lines 437–447
**Description:**
Setting `is_loading = True` writes to `is_project_loading` on the current
`ProjectState` but does not call `self.notify()`. The UI will not reflect
the loading state change until the next unrelated event triggers a refresh.
**Fix:** Add `self.notify()` at the end of the `is_loading` setter.

---

### C10 — `page_model.py:image_path` property silently swallows setter failures

**File:** `pd_ocr_labeler/models/page_model.py` ~lines 67–81
**Description:**
The `image_path` setter has `except Exception: pass` around
`self.page.image_path = value`. Silent swallowing means a frozen or
read-only page object leaves `self._image_path` and `self.page.image_path`
permanently inconsistent, with no log entry or exception.
**Fix:** At minimum log the exception at DEBUG level; or remove the catch
and let the caller handle it.

---

### C11 — Tests overwrite user settings with test directory state

**Description:**
When running tests, the app forgets the previously selected project directory and next time
it runs it sends the user to the test projects directory. The tests shouldn't write the test
directory state to the local user settings. Where are local user settings stored? should be
in similar place to .cache or .local etc.
