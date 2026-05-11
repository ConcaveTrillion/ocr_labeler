# OCRConfigModal Negative-Path Apply Test: Wiring Attempt

Iter 43 / 2026-05-06. Concrete attempt to add a browser test that
exercises the `_apply_selection` False branch in
`pd_ocr_labeler/views/header/ocr_config_modal.py`. **Outcome:
infeasible without a production-side change.** This note documents
the architectural obstacle so future iterations can stop deferring
the carry-over and route it to "needs human approval" instead.

## What we wanted to cover

`OCRConfigModal._apply_selection` (lines 179-218) calls

```python
success = self.app_state_model.command_set_selected_ocr_models(
    detection_key, recognition_key,
)
if success:
    self._notify("OCR models updated", "positive")
    if self._dialog is not None:
        self._dialog.close()
else:
    self._notify("Failed to apply OCR models", "negative")
```

All eight existing browser tests in `tests/browser/test_ocr_config_modal.py`
cover the success path. The False branch (modal stays open, negative
notification shown) is uncovered.

## What we tried

### Attempt 1: Class-level monkeypatch in a pytest fixture

The original plan was to monkeypatch `AppStateViewModel.command_set_selected_ocr_models`
to return False before the page loads:

```python
@pytest.fixture
def force_apply_failure(monkeypatch):
    from pd_ocr_labeler.viewmodels.app.app_state_view_model import AppStateViewModel
    monkeypatch.setattr(
        AppStateViewModel,
        "command_set_selected_ocr_models",
        lambda self, *a, **kw: False,
    )
```

The modal calls `self.app_state_model.command_set_selected_ocr_models(...)`
via direct attribute access (confirmed at line 209), so a class-level
patch *would* affect all future instances within the same Python
process — Python falls back to class lookup for missing instance attrs.

**Why it fails:** `tests/browser/conftest.py:42-126` (the
`browser_app_url` fixture) starts the NiceGUI app as a separate
**subprocess** via `subprocess.Popen([sys.executable, "-m", "pd_ocr_labeler.cli", ...])`.
A `monkeypatch` mutation in the pytest test process has zero effect
on the subprocess's `AppStateViewModel` class object; they are
distinct interpreter instances.

### Attempt 2: Drive the select to an out-of-options value

Could we send an arbitrary string into the detection/recognition
select via `page.evaluate(...)` and trigger Apply? The state-layer
`set_selected_ocr_models` (`pd_ocr_labeler/state/app_state.py:317-336`)
naturally returns False when either key is not in `available_ocr_models`,
so an invalid select value would walk the failure path organically.

**Why it fails:** NiceGUI's `ChoiceElement._update_options` (verified
in the installed `nicegui.elements.choice_element` source) maps
client values through an index lookup before storing them on
`self.value`:

```python
if not isinstance(before_value, list):
    self.value = before_value if before_value in self._values else None
```

A client-side value not in `_values` becomes `None`, which then short-
circuits earlier in `_apply_selection` ("Select both detection and
recognition models first" warning, NOT the False branch we want).
There is no way through the websocket protocol to set a select's
server-side `value` to an arbitrary string outside the options list.

### Attempt 3: Pre-corrupt `selected_ocr_*_model_key` via fixtures

`set_selected_ocr_models` returns False on key-not-in-options. If the
pre-saved fixture state had `selected_ocr_detection_model_key` set
to a name that's not in `available_ocr_models`, `_open` would still
reset the select to that key (lines 117-119), and Apply would walk
the False branch.

**Why it fails:** `available_ocr_models` is rebuilt from the live
HF probe + trainer-output discovery on every app start; the persisted
config doesn't carry an authoritative model registry. Even if we
seeded `selected_ocr_detection_model_key="ghost"` in `xdg_config_home`,
the modal's `_open` handler at line 117 reads `selected_ocr_detection_model_key`
back from `app_state_model`, which goes through getters that may
re-validate. More importantly, this would be testing a
state-corruption scenario that doesn't reflect the real failure mode
the negative-path branch is *meant* to handle (the branch exists
because of the AppStateViewModel try/except wrapper at lines 266-281
catching unexpected exceptions from `self._app_state.set_selected_ocr_models`,
not key-validation failures, which themselves are nominal returns).

### Attempt 4: HTTP test-hook endpoint

Could we POST to the running subprocess's `/test/force_apply_failure`
endpoint? **No such endpoint exists**, and adding one is a production-code
change.

## Conclusion

The obstacle is **architectural**, not tactical. The browser fixture
runs the app out-of-process, so in-process monkeypatching cannot
reach `AppStateViewModel`. The only viable paths require a
production-code change:

1. **Env-var test hook** — `_apply_selection` (or the underlying
   command) honors `PD_OCR_LABELER_TEST_FORCE_APPLY_FAILURE=1` to
   short-circuit return False. Five lines of production code, plus
   the env var threaded into the browser fixture. **Requires human
   approval** under overnight rules.
2. **In-process browser fixture** — restructure
   `tests/browser/conftest.py:42` to start NiceGUI inside the pytest
   process (e.g. via a thread + `ui.run(reload=False)`). This would
   enable monkeypatching for **every** browser test, but it's a
   far-reaching infra change touching every browser test's lifecycle
   assumptions. **Requires human approval** under overnight rules.
3. **Targeted unit test of `_apply_selection` directly** — bypass
   the browser entirely. Build the modal in-process with a fake
   `AppStateViewModel` whose `command_set_selected_ocr_models`
   returns False, click Apply by calling the coroutine directly, and
   inspect the dialog's `is_open` flag and the captured notify
   calls. This avoids the subprocess obstacle and stays test-side.
   **Viable in a future iteration without production changes**, but
   requires standing up a new test fixture pattern (no existing
   modal-unit-test surface to copy from).

## Recommendation for the queue

Move the carry-over from "deferred" to **"infeasible without
production hook OR in-process unit-test fixture, both needing human
approval."** Concretely: drop it from the top-3 next-candidate queue
and re-route under a "blocked on human" header in
`docs/planning/next-step.md`.

## What did NOT work and what bytes the next attempt should NOT spend

- Do **not** retry class-level `monkeypatch.setattr`. It cannot
  reach a subprocess.
- Do **not** retry driving the select to an invalid value via
  Playwright `evaluate`. NiceGUI's choice-element protocol filters.
- Do **not** invent a new "ghost-model" config-seeding fixture; it
  would test the wrong branch of `set_selected_ocr_models`.

The next bytes should go into either (a) a new in-process
modal-unit-test pattern (requires a green-light from the human on
test-architecture direction), or (b) a tiny env-var production hook
(requires human approval per overnight rules).

## Files inspected (for reproducibility)

- `pd_ocr_labeler/views/header/ocr_config_modal.py` — `_apply_selection`
  at lines 179-218 confirmed direct-attribute call shape.
- `pd_ocr_labeler/viewmodels/app/app_state_view_model.py` — lines
  266-281 confirmed try/except wrapper around `set_selected_ocr_models`.
- `pd_ocr_labeler/state/app_state.py` — lines 317-336 confirmed
  natural False return on key-not-in-options.
- `pd_ocr_labeler/cli.py` — confirmed no test-hook CLI argument
  exists.
- `tests/browser/conftest.py` — confirmed subprocess-based fixture
  architecture at lines 42-126.
- `tests/browser/test_ocr_config_modal.py` — confirmed all 8 tests
  cover only the success path.
- NiceGUI installed source `nicegui.elements.choice_element.ChoiceElement`
  — confirmed value-to-options filtering at `_update_options`.
