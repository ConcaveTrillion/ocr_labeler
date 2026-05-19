# OCRConfigModal State Machine Deep Review (Iter 33)

Date: 2026-05-06

Scope:

- `pd_ocr_labeler/views/header/ocr_config_modal.py` (179 LOC)
- `pd_ocr_labeler/state/app_state.py` lines 90-350 (state-side
  refresh / selection / pin setters)
- `pd_ocr_labeler/viewmodels/app/app_state_view_model.py` lines
  26-290 (UI-bound viewmodel + commands)
- `pd_ocr_labeler/operations/ocr/model_selection_operations.py`
  lines 160-400 (`fetch_hf_last_modified`, `discover_model_options`)
- `tests/browser/test_ocr_config_modal.py` (8 browser tests)
- `tests/pd_ocr_labeler/state/test_app_state.py::test_set_selected_ocr_models_*`
  / `test_set_hf_pinned_revision_*` (state-level coverage)

This review consolidates the empirical behavior captured by 9
iterations of test work (iters 13/14/15/25/27/28/29/30/32) and
identifies coverage gaps and real bugs / smells in the modal's
apply / cancel / rescan state machine.

## 1. Executive Summary

The OCRConfigModal is a single dialog over three logically independent
mutable inputs (detection select, recognition select, HF revision
input) with three actions (Cancel, Apply, Rescan Models). The
state machine has good lifecycle hygiene on Cancel and Apply
(both reset cleanly via `_open` re-applying canonical values) but
several subtle correctness smells worth flagging:

1. Rescan Models partial commit — Rescan calls
   `command_refresh_ocr_models` (which mutates `available_ocr_models`
   on the underlying `AppState`) BEFORE the user has pressed Apply.
   If the user then presses Cancel, the option lists in state have
   already changed; only the visible select values in the dialog
   revert. This is intentional ("Rescan probes the world") but is
   undocumented and asymmetric with the HF-revision-input contract.
2. HF revision text edits cancel-revert via a re-open hack — the
   modal does NOT track a "pristine" baseline; it relies entirely on
   `_open` resetting the input to `app_state.hf_pinned_revision or ""`
   on the NEXT open. There is no separate revert path for an in-place
   undo, and any code that `dialog.open()`s the modal while skipping
   `_open` would skip the reset and leave stale typed values visible.
3. `_apply_selection` ordering is brittle — it calls
   `command_set_hf_pinned_revision` (which itself triggers a full
   `refresh_ocr_models` notify) THEN
   `command_set_selected_ocr_models` against keys read from the
   selects BEFORE the rescan. If the rescan removed the displayed
   detection/recognition keys, the second call returns `False` and
   surfaces "Failed to apply OCR models" without explaining to the
   user that their pin choice already mutated app state.
4. Apply on selection-validation failure leaks a partial pin
   commit — when `set_selected_ocr_models` returns `False` (key not
   in `available_ocr_models`), the modal stays open with a negative
   notification, but `set_hf_pinned_revision` already mutated
   `self.hf_pinned_revision` and refreshed model lists. The user is
   shown a single negative toast, no rollback, and the dialog is in
   a state where Apply will succeed on retry only because the lists
   refreshed. This is a real partial-commit bug.
5. No browser regression covers the partial-commit failure path
   or the post-Rescan-then-Cancel partial commit. Both are real
   user-observable behaviors that deserve at least an asserting test.

## 2. State Diagram

States: `Closed`, `OpenPristine`, `OpenDirty(field-set)`.
Inputs: `t` (trigger click), `c` (Cancel), `a` (Apply), `r` (Rescan).

```text
              t (open)                edit-input
   Closed --------------> OpenPristine --------> OpenDirty
     ^   <----- c -----------/    \----- r ---->
     |                                            \
     |   <----- a (success) ----------------------
     |   stay (a failure)                          OpenDirtyAfterRescan
     |   stay (r) -------------------------> always re-renders selects
```

Key facts:

| Transition | Mutates AppState? | Mutates dialog UI? | Closes dialog? |
| --- | --- | --- | --- |
| `t` (open) | Yes (re-runs `refresh_ocr_models` via `_open`) | Yes (resets every field to canonical) | No (opens) |
| `c` (Cancel) | No | No | Yes |
| `r` (Rescan) | Yes (re-runs `refresh_ocr_models`) | Yes (re-applies options + maybe value) | No |
| `a` (Apply, OK) | Yes (pin +/- selection) | No (closes) | Yes |
| `a` (Apply, fail) | Possibly partial (pin yes, selection no) | No | No |

## 3. Inputs and What Each Writes To

| UI control | Writes (on Apply) | Notify? |
| --- | --- | --- |
| `dialog-detection-model-select` | `AppState.selected_ocr_detection_model_key` | Yes |
| `dialog-recognition-model-select` | `AppState.selected_ocr_recognition_model_key` | Yes |
| `ocr-hf-revision-input` | `AppState.hf_pinned_revision` and triggers `refresh_ocr_models` | Yes |
| Rescan button | `AppState.available_ocr_models` (re-discovery); resets selects | Yes |

The selects' `value` does NOT propagate to `AppState` until Apply is
pressed. Editing is purely local to the q-select widget. Same for the
HF revision input: typing does not mutate state until Apply.

`_open` is the canonical reset: it copies `AppState`'s current values
into each widget. It also calls `command_refresh_ocr_models`,
meaning every open is also a rescan.

## 4. Notable Findings / Bugs / Smells

### 4.1 Partial-commit bug in `_apply_selection` (real bug, low frequency)

Sequence:

1. User opens modal.
2. User types a new HF revision and (somehow) leaves the detection
   select on a stale key that won't survive the rescan.
   (Reproduction path: paste a pin, click Rescan, the select reverts
   to canonical, paste a different pin, click Apply.)
3. `_apply_selection` calls `command_set_hf_pinned_revision(new_pin)`.
   `set_hf_pinned_revision` mutates `AppState.hf_pinned_revision` AND
   triggers `refresh_ocr_models(notify=True)`. State is now committed.
4. `_apply_selection` then calls
   `command_set_selected_ocr_models(detection_key, recognition_key)`.
   `detection_key` was read from the widget BEFORE step 3, but
   `available_ocr_models` was just rebuilt — if the local key the
   widget held is gone, this returns `False`.
5. Modal stays open with "Failed to apply OCR models" notification.
   `AppState.hf_pinned_revision` is already changed but the user's
   selection failed. No rollback.

Recommendation: Either (a) read the select values AFTER the rescan
inside `_apply_selection` (refresh widget values from the new
canonical keys), or (b) commit pin and selection atomically by
introducing a single `AppState.apply_ocr_config(pin, det, rec)`
that validates pre-mutation. Option (b) is cleaner.

### 4.2 Rescan partial-commit before Cancel (intentional but undocumented)

Rescan calls `command_refresh_ocr_models` directly. This mutates
`AppState.available_ocr_models`, `ocr_detection_model_options`,
`ocr_recognition_model_options`, and emits a `notify()`. The user
can then press Cancel — and the in-state option lists remain
changed. Only the visible select values in the dialog "revert" via
`_open` on next trigger.

This is fine if Rescan is conceptually "probe the world; the
world doesn't care about the dialog's lifecycle". But the symmetry
with the HF revision input (where typing is purely local until Apply)
is broken, and there is no UI signal that Rescan committed something
beyond the dialog. A small surfaced affordance ("Models refreshed —
will use new list on next OCR") would help.

### 4.3 `_open` always rescans (cost on each open)

Every open of the modal triggers `command_refresh_ocr_models`, which
does an HF probe with a 5s timeout. On a cold/offline network, the
modal can take up to 5 seconds to appear because the open handler
synchronously waits for `discover_model_options` to return. The
test fixture works around this because the HF probe fails fast in
the offline CI environment.

Recommendation: cache the last `refresh_ocr_models` time and skip
auto-refresh on `_open` if it ran recently (say less than 30 s ago);
add an explicit Rescan to invalidate the cache on demand.

### 4.4 No revert on stale selection after Rescan inside same open

If the user opens the dialog with detection key `X`, presses
Rescan, and the rescan removes `X` (e.g. another process moved the
trainer outputs), the dialog handler sets the select's value to
the new `selected_ocr_detection_model_key` (which
`_ensure_selected_ocr_keys_are_valid` auto-picked). This is the
right behavior, but it occurs silently. The user's typed pin is
preserved (good), but their pre-Rescan detection selection is lost
(no toast).

### 4.5 `_close` is a thin wrapper that bypasses `_open` reset semantics

`_close` simply calls `self._dialog.close()`. There is no analog of
`_open`'s reset on close. So if some future code path causes
`_dialog.close()` to fire without going through Cancel (e.g. Esc
key, backdrop click) and the next open is from somewhere that does
NOT call `_open` (e.g. NiceGUI's internal handling), typed values
could survive. As of today, all paths route through `_open`, so
this is latent — but a stale-state hazard if anything ever opens
the dialog without going through the trigger button.

### 4.6 Apply success uses positive toast; Apply failure uses negative — correct

This is well-handled. The browser test
`test_ocr_config_apply_with_no_edits_closes_without_error` asserts
no `bg-negative` notification. Symmetric coverage of the failure
path is missing.

## 5. Coverage Matrix

| Invariant | Test asserting it | Gap? |
| --- | --- | --- |
| Trigger button visible at app start | `test_ocr_config_trigger_button_present` | No |
| Click trigger -> dialog footer controls visible | `test_ocr_config_modal_opens_on_trigger_click` | No |
| Cancel closes dialog (footer hidden) | `test_ocr_config_cancel_closes_modal` | No |
| No-edit Apply closes dialog with no negative toast | `test_ocr_config_apply_with_no_edits_closes_without_error` | No |
| HF revision typed value reverts on Cancel | `test_ocr_config_hf_revision_edit_reverts_on_cancel` | No |
| HF revision typed value persists through Apply | `test_ocr_config_hf_revision_edit_persists_through_apply` | No |
| Det / reco select wrappers open menus + survive Cancel cycle | `test_ocr_config_model_selects_open_menu_and_survive_cancel` | No |
| Rescan Models does not error / leaves dialog open | `test_ocr_config_rescan_models_does_not_error` | No |
| `set_selected_ocr_models` accepts different det/reco keys | `test_set_selected_ocr_models_updates_detection_and_recognition` | No |
| `set_hf_pinned_revision` triggers a refresh with the new pin | `test_set_hf_pinned_revision_triggers_refresh` | No |
| Empty/whitespace pin clears the pin | `test_set_hf_pinned_revision_clears_when_empty_string` | No |
| Det / reco select VALUE cancel-revert (not just menu open) | (none — iter-15 priority item 1: needs trainer-output fixture) | YES |
| Det / reco select VALUE persists through Apply | (none — same blocker) | YES |
| Apply with stale select key (not in `available_ocr_models`) fails cleanly | (none) — should assert: negative toast + dialog stays open | YES |
| Apply with stale key DOES NOT leak pin commit (rollback or atomic) | (none) — currently this would FAIL because there is no rollback. See finding 4.1. | YES |
| Rescan changing options updates the visible select values | (none) — needs fixture to mutate trainer outputs between rescans | YES |
| Rescan + Cancel: option lists in state ARE persisted (intentional) | (none) — could be a state-layer test once mockable | YES |
| `_open` always re-applies canonical select values | partially via `test_ocr_config_model_selects_open_menu_and_survive_cancel` | partial |
| HF probe failure path emits negative notification | (none) — would need monkeypatch to force `refresh_ocr_models` to raise | YES |
| Detection key validity on Apply (key absent in `available_ocr_models`) | (none) — would need to manipulate select via JS or add a test fixture | YES |

## 6. Recommended Follow-Up Work, Ranked

### Tier 1 — real bugs

1. Atomic Apply (finding 4.1). Refactor `_apply_selection` to
   resolve pin and selection in one transactional state-layer call
   that validates BEFORE mutating. Test: a state-level unit test
   that calls a new `AppState.apply_ocr_config(pin, det, rec)`,
   asserts no mutation when `det` is invalid even if `pin` is new.
2. Negative-path browser test for `_apply_selection`. Add a
   fixture or monkeypatch path that returns `False` from
   `command_set_selected_ocr_models`, click Apply, assert dialog
   stays open and a negative toast appears. Today this path is
   dead in the production tests.

### Tier 2 — coverage gaps that don't need new fixtures

1. `_open` resets HF revision input even when state is unchanged.
   Add a state-layer-bypass browser test: open, type, Cancel, and
   assert the input's `input_value()` was actually re-set on
   re-open, distinct from "didn't persist". (The current cancel-revert
   test asserts the value matches the initial baseline; this would
   prove `_open` IS the mechanism, not a side effect of dialog
   re-mount.)
2. HF probe failure surfacing. Monkeypatch
   `ModelSelectionOperations.discover_model_options` to raise; click
   Rescan; assert negative toast fires and dialog stays open.

### Tier 3 — needs new fixtures

1. Trainer-output fixture providing >=2 selectable options —
   unblocks the long-queued iter-15 candidate (full select
   value-cancel-revert) plus several new tests:
   - Apply with edited detection/recognition values persists.
   - Cancel after edit reverts both select values.
   - Rescan that removes the displayed key auto-falls-back to
     auto-picked key.

### Tier 4 — UX / architecture

1. `_open` re-rescan cost. Add caching (last-rescan timestamp);
   skip rescan on open if recent.
2. Atomic state-layer command. Introduce
   `AppState.apply_ocr_config(pin, det, rec)` that validates first,
   mutates atomically, notifies once. Replaces the modal's
   two-call sequence with a single intent.
3. Document the Rescan-vs-Cancel asymmetry in user-facing docs.
   `docs/usage/how-to-label-a-page.md` currently does not mention
   the OCR Configuration modal; add a short paragraph explaining
   that Rescan probes the world (committed immediately) and the
   selects/pin are "edit-then-Apply" controls.

## Appendix: Path Map (where to make changes)

| Change | Likely files |
| --- | --- |
| Atomic Apply | `pd_ocr_labeler/state/app_state.py` (new method), `pd_ocr_labeler/viewmodels/app/app_state_view_model.py` (new command), `pd_ocr_labeler/views/header/ocr_config_modal.py::_apply_selection` |
| Trainer-output fixture | `tests/browser/conftest.py` or new helper, used by `tests/browser/test_ocr_config_modal.py` |
| Rescan caching | `pd_ocr_labeler/state/app_state.py::refresh_ocr_models` (timestamp), `views/header/ocr_config_modal.py::_open` |
| Negative-path Apply browser test | `tests/browser/test_ocr_config_modal.py` (new test + monkeypatch hook) |
| HF probe failure surfacing | `tests/browser/test_ocr_config_modal.py` and a state-level test in `tests/pd_ocr_labeler/state/test_app_state.py` |
