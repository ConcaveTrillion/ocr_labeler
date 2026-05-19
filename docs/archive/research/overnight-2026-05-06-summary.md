# Overnight loop summary — 2026-05-06

A `/loop` ran 46 iterations on `pd-ocr-labeler` overnight. This document
catalogues what was committed, what was reviewed, and what findings
need your attention.

---

## At a glance

- **46 iterations completed.** Iteration 47 was interrupted at start.
- **41 commits landed** (branch `master`, **41 ahead of `origin/master`**, nothing pushed).
- **Tests:** ~898 → **949** (+51 net new passing tests).
- **`make ci` is meaningfully denoised** — two pre-existing flakes were fixed or mitigated
  mid-night, so retry overhead is gone.
- **Pre-existing WIP `stash@{0}` was preserved untouched** all night (per overnight rules).
- **One file is staged but uncommitted**:
  `docs/review-notes/2026-05-06-notification-mixin-dedup.md` — appears to be in-flight
  from the interrupted iteration 47. Decide whether to keep, discard, or finish it.

Total diff: **35 files changed, 5,037 insertions, 276 deletions.**

---

## Commits, grouped by workstream

### Stable-testid backfill (12 commits, iters 1–12)

Added `data-testid` attributes across the UI to enable reliable
Playwright selectors and unblock automated labeling. The rollout
saturated by iter 12 and remaining work pivoted to coverage.

| SHA | Subject |
| --- | --- |
| `f2f1c61` | testids on PageActions buttons |
| `83960ee` | testids on ProjectNavigationControls |
| `757df55` | testids on ProjectLoadControls + source folder dialog |
| `eb2a41f` | testids on OCRConfigModal controls |
| `b1c5962` | selects on word_match_toolbar |
| `3d9afb4` | word edit dialog selects + nudge buttons |
| `b3864dc` | dialog tag-chip area + zoom toggle |
| `6e05242` | renderer tag-chips row |
| `25f4248` | dialog preview columns |
| `0bd57ff` | dialog header label |
| `f8acdf1` | nav page input + total label |
| `ea9a948` | paragraph label button |

### CI denoising (2 commits)

| SHA | Iter | Subject |
| --- | --- | --- |
| `533461a` | 26 | Fix `test_app_state.py` xdist-pollution flake. Root cause: pytest's dotted-string resolver tripped on `pd_ocr_labeler.state.state` lookup under xdist. Fix: switched 4 monkeypatches to class-object form. Verified across 2 consecutive `make ci` runs. |
| `62532c8` | 31 | Mitigate `test_load_button_prevents_multiple_clicks` flake. Diagnosed across 3 cycles. Surfaced the `run.io_bound` racy-`None` underlying bug (still needs a real fix — see findings). Verified 3/3 clean `make ci` runs. |

### OCRConfigModal coverage (15 commits)

The modal had **0 browser tests at start**, no unit tests, and a full
testid contract from iter 4. Built coverage in two arcs.

**Browser tests** (iters 13/14/15/25/27/28/29/30/32, 9 commits):

| SHA | Iter | Subject |
| --- | --- | --- |
| `9fa6b8e` | 13 | Open / cancel / trigger-visible smoke (3 tests) |
| `8e21d7c` | 14 | HF revision input cancel-revert |
| `e14e685` | 15 | Model-select open/cancel lifecycle |
| `9fd7e65` | 25 | No-edit Apply round-trip (verified `_apply_selection` skips HF probe when nothing changed) |
| `398414b` | 27 | Apply with HF revision edit (round-trip persistence) |
| `8694416` | 28 | In-dialog Apply-Style dropdown drive (non-default value) |
| `4896f48` | 29 | In-dialog Apply-Component dropdown drive |
| `491e8a0` | 30 | In-dialog Apply-Scope dropdown drive (closes the dialog dropdown trio) |
| `eb281d0` | 32 | Rescan Models smoke (no negative notification + modal stays responsive) |

**Unit tests** (iters 44/45/46, 3 commits):

After iter 43 documented that subprocess-fixture browser tests can't
be monkeypatched, iter 44 unlocked an in-process unit-test pattern:
construct the modal directly with mocked state. This proved highly
productive.

| SHA | Iter | Subject |
| --- | --- | --- |
| `fadb514` | 44 | 10 unit tests pinning HF-revision Cancel-revert (proves it's *open-driven*, not close-driven) |
| `5813183` | 45 | 5 unit tests on `_apply_selection` (success/guard/**partial-commit characterization**) |
| `d915420` | 46 | 4 unit tests on `_rescan_models` (success/failure/recovery/None-selects) |

### Toolbar split-family coverage (6 commits)

| SHA | Iter | Subject |
| --- | --- | --- |
| `f7e8fec` | 16 | line-expand-bboxes parametric + click |
| `906d472` | 18 | paragraph-expand-bboxes parametric + click |
| `076b546` | 19 | line-split-after-word click test (line count 7→8) |
| `2049ca9` | 20 | line-split-by-selection (1-word, +1) |
| `6d88501` | 22 | Cross-line split-by-selection (+2 delta) |
| `b464098` | 24 | Non-contiguous within-line split-by-selection (+1) |

### Persistence round-trip coverage (3 commits)

Closed the per-flag persistence gap class entirely.

| SHA | Iter | Subject |
| --- | --- | --- |
| `75b211c` | 36 | `right_footnote` round-trip + legacy `footnote` migration (migration logic was completely untested — 0 hits on `"footnote"` literal) |
| `8e57908` | 37 | `small_caps` / `blackletter` / `left_footnote` round-trip |
| `90d6cc8` | 38 | `italic` + multi-flag combination round-trip |

### Misc fresh gaps (3 commits)

| SHA | Iter | Subject |
| --- | --- | --- |
| `9abb52b` | 35 | Erase Pixels button (only image-tab control without coverage) |
| `bfb71f6` | 40 | Source-folder Enter on nonexistent path (negative-path notification) |
| `6609f6b` | 41 | Unchanged-value Enter on dialog GT input (silent-success-path invariant) |

### In-dialog tag-chip clear (1 commit)

| SHA | Iter | Subject |
| --- | --- | --- |
| `fa2a1eb` | 23 | In-dialog per-chip style-clear affordance (Apply Style → hover chip → clear icon → chip count drops) |

### Documentation & deep reviews (6 commits)

| SHA | Iter | Subject | Headline finding |
| --- | --- | --- | --- |
| `b990a4b` | 17 | Refresh `next-step.md` priority list against real coverage | All "0%" claims were grossly stale |
| `0b0c2fe` | 21 | Toolbar split-family review | Three split ops are distinct only in multi-word/cross-line cases |
| `38ceaba` | 33 | OCRConfigModal state-machine review | **Partial-commit bug** in `_apply_selection` |
| `f89e8fb` | 34 | Browser-test selection helpers review | `_setup` duplicated 11×, 162 `wait_for_timeout` calls |
| `907a820` | 39 | Keyboard-shortcut coverage review | Only 6 registered shortcuts; 1 untested + UX asymmetry |
| `4ee2b7b` | 42 | Async handler races review | **5 new findings** including stale-closure correctness bug |
| `39e8387` | 43 | Monkeypatch wiring infeasibility | Subprocess fixture is the architectural obstacle |

---

## ⚠ Findings that need your attention

These were discovered during overnight reviews and characterization
tests but **not fixed** — they require production-code changes that
the loop deferred to your judgment. Ranked roughly by severity.

### 1. `_background_load` stale-closure correctness bug (iter 42, Finding E)

**Severity: medium-high. Real correctness bug.**

- File: `pd_ocr_labeler/state/project_state.py:944-950`
- `_background_load` reads `self.current_page_index` *before* the
  `run.io_bound` await, but `_update_text_cache(force=True)` reads it
  *after*. A fast double-navigation (e.g. user mashes Next twice
  while page 1 is still loading) populates the text cache for the
  wrong page.
- **Fix sketch**: capture `target_index` into a local before the
  await, gate the post-await text-cache update on stable-target.
  Single-file fix, narrow diff.

### 2. OCRConfigModal `_apply_selection` partial-commit bug (iter 33 finding 4.1, characterized in iter 45)

**Severity: medium. Demonstrated by failing-by-design test.**

- File: `pd_ocr_labeler/views/header/ocr_config_modal.py` `_apply_selection`
- When the HF revision pin changes AND the post-rescan selection key
  is gone, `command_set_hf_pinned_revision` already mutated state
  before `command_set_selected_ocr_models` returns False. **No
  rollback** — pin is committed; selection is not; user sees a
  negative notification but the pin change persisted silently.
- **Already test-pinned**: the iter-45 unit test
  `test_models_failure_after_pin_commit_leaves_pin_committed` will
  fail when this is fixed (it's a characterization test).
- **Fix sketch**: introduce an atomic `apply_ocr_config(pin, det,
  rec)` viewmodel command that does both writes inside a single
  try-validate-commit block.

### 3. GT-input Tab navigation is silently broken (iter 40)

**Severity: medium. UX-visible, easy fix.**

- File: `pd_ocr_labeler/views/projects/pages/word_match_gt_editing.py:155-183`
- `_focus_word_gt_input` calls `input_element.focus()`, but NiceGUI's
  `ui.input` does NOT define a `focus` method. Inside `ui.timer(0,
  ...)`, the resulting `AttributeError` is silently swallowed.
- **User impact**: Tab from a GT input drops focus on `<body>`
  instead of advancing to the next GT input. The browser test for
  this shortcut never landed because the bug makes the assertion
  unwriteable.
- **Fix sketch**: replace `input_element.focus()` with
  `input_element.run_method("focus")` (one-line change). Then land
  the queued Tab/Shift+Tab browser test.

### 4. `run.io_bound` racy `None` return for ground-truth load (iter 31)

**Severity: medium. Mitigation in place; root cause unaddressed.**

- Under heavy xdist load, `await run.io_bound(load_ground_truth_from_directory, ...)`
  occasionally returns `None`, triggering a `'NoneType' has no len()`
  warning and a fallback empty-map load path. Project loads
  eventually but takes >3s.
- Iter 31 mitigated by bumping retries to 100 in
  `tests/integration/test_project_loading.py`. The underlying
  `run.io_bound` `None` return is still unexplained.
- **Fix sketch**: investigate why `run.io_bound` returns `None`
  under load; once fixed, drop iter-31's `retries=100`.

### 5. Other async-handler race findings (iter 42)

| Finding | File:line | Severity | Description |
| --- | --- | --- | --- |
| **D** | `views/projects/pages/export_dialog.py:200-256` | medium | No double-click guard on Export button; concurrent `_run_export` calls could write the same subfolder non-deterministically. |
| **F** | `app.py:302` | low | URL-init `ui.timer(0.05, ...)` missing `once=True` and `active=False` cleanup in `on_disconnect`; per-session timer leak. |
| **G** | `views/projects/pages/page_view.py:377, 427` | medium | `command_reload_page_with_ocr()` is sync inside an async handler; blocks the event loop for multi-second OCR latency. |
| **I** | `views/projects/pages/page_view.py:243, 267, 294, 320, 346` | medium | Sync `command_save_*` / `command_refine_*` calls inside async handlers freeze the UI during pd-book-tools work. |

### 6. OCRConfigModal `_open` always rescans (iter 33 finding 4.2)

**Severity: medium. UX-visible.**

Every modal open triggers `command_refresh_ocr_models`, which can
stall up to 5s on cold/offline networks. Recommend short-window
rescan caching.

### 7. Negative-path Apply browser test infeasibility (iter 43)

**Severity: testing infrastructure decision needed.**

The browser-test fixture launches NiceGUI in a *subprocess*; pytest's
`monkeypatch` cannot reach it. Two viable forward paths, both
documented in `docs/review-notes/2026-05-06-monkeypatch-wiring-attempt.md`:

- **Option A (5 lines)**: add `PD_OCR_LABELER_TEST_FORCE_APPLY_FAILURE=1`
  environment-variable production hook.
- **Option B (broader)**: introduce an in-process modal-unit-test
  fixture pattern. (Iters 44–46 already proved this pattern is
  viable for non-browser unit tests.)

The negative-path Apply assertion can also stay at the unit-test
level forever (iter 45 already covers it there), in which case no
browser test is needed.

### 8. Cross-repo: `+2` line-delta discrepancy (iter 23, planning-doc gap 8)

**Severity: low. Investigation, not a fix.**

- Iter 23 found that `word-form-line-button` cross-line empirically
  produces a `+2` line delta on the live fixture, contradicting the
  iter-21 review's predicted `+1`. Origin unclear: labeler dispatch
  divergence vs `pd-book-tools` unit-test fixtures being too
  synthetic.
- **Needs `pd-book-tools` agent**: add a unit test that mirrors the
  live fixture's exact paragraph/line layout and prints pre/post
  output, to root-cause the discrepancy.

### 9. Test-infrastructure cleanup (iter 34)

**Severity: low. Quality of life.**

- `_setup` is duplicated across 11 browser test files.
- `_select_word` / `_select_line` / `_select_paragraph` /
  `_switch_to_all_lines` / `_wait_for_notification` /
  `_get_gt_inputs` / `_get_ocr_labels` are each duplicated 2–5×.
- 162 `wait_for_timeout` calls across browser tests are candidates
  for an `expect()`-driven audit.
- `test_word_ctrl_click_multi_select` / `_deselect` use
  `modifiers=["ControlOrMeta"]` on plain checkboxes — possibly
  tautological tests.

A centralization pass would be a broad diff (touches all 11 browser
test files); should land as one PR with intent confirmation.

### 10. Other lower-priority observations

- **`_close` has no reset semantics** (iter 33 finding 5) — latent
  stale-state hazard if any future code path bypasses `_open`.
- **HF revision input has no Enter handler** (iter 39) — UX
  asymmetry vs the source-folder path-input which does.
- **Quasar Escape-to-close** is the only Escape coverage; a future
  commit adding `persistent` to a dialog would silently regress
  three tests (iter 39).

---

## Files changed (categorized)

### Production code (testid-only changes)

```text
pd_ocr_labeler/views/header/ocr_config_modal.py
pd_ocr_labeler/views/header/project_load_controls.py
pd_ocr_labeler/views/projects/pages/page_actions.py
pd_ocr_labeler/views/projects/pages/word_edit_dialog.py
pd_ocr_labeler/views/projects/pages/word_match_renderer.py
pd_ocr_labeler/views/projects/pages/word_match_toolbar.py
pd_ocr_labeler/views/projects/project_navigation_controls.py
```

All changes are `data-testid` `.props(...)` additions. **Zero
behavior changes** to production code.

### Tests added/modified

```text
tests/browser/helpers.py                                       (selector migrations)
tests/browser/test_browser_smoke.py                            (selector migrations)
tests/browser/test_home_page.py                                (selector migrations)
tests/browser/test_image_tabs.py                               (Erase Pixels)
tests/browser/test_keyboard_shortcuts.py                       (testid + Enter tests)
tests/browser/test_navigation.py                               (selector migrations)
tests/browser/test_ocr_config_modal.py                         (NEW — 8 browser tests)
tests/browser/test_page_actions.py                             (selector migrations)
tests/browser/test_project_loading.py                          (selector migrations)
tests/browser/test_session_isolation.py                        (selector migrations)
tests/browser/test_source_folder_dialog.py                     (selector migrations + Enter neg path)
tests/browser/test_toolbar_line_actions.py                     (split family + expand-bboxes)
tests/browser/test_toolbar_paragraph_actions.py                (paragraph-expand-bboxes)
tests/browser/test_word_edit_dialog.py                         (dropdown trio + chip clear)
tests/browser/test_word_match.py                               (renderer tag-chip row)
tests/browser/test_word_match_line_actions.py                  (paragraph label button)
tests/integration/test_project_loading.py                      (load-button flake mitigation)
tests/pd_ocr_labeler/operations/persistence/test_save_load_round_trip.py  (NEW persistence)
tests/pd_ocr_labeler/state/test_app_state.py                   (xdist pollution fix)
tests/pd_ocr_labeler/views/header/test_ocr_config_modal.py     (NEW — 19 unit tests)
```

### Documentation & reviews

```text
docs/architecture/ui-action-buttons.md                         (testid columns)
docs/planning/next-step.md                                     (priority list refresh + per-iter "Done" entries)
docs/review-notes/2026-05-06-async-handler-races.md            (iter 42 review)
docs/review-notes/2026-05-06-browser-test-selection-helpers.md (iter 34 review)
docs/review-notes/2026-05-06-keyboard-shortcuts-coverage.md    (iter 39 review)
docs/review-notes/2026-05-06-monkeypatch-wiring-attempt.md     (iter 43 obstacle doc)
docs/review-notes/2026-05-06-ocr-config-modal-state-machine.md (iter 33 review)
docs/review-notes/2026-05-06-toolbar-split-family.md           (iter 21 review)
```

### Uncommitted (interrupted iter 47)

```text
docs/review-notes/2026-05-06-notification-mixin-dedup.md       (staged, 221 lines)
```

This file appears mid-flight from iteration 47 (which I rejected
before it ran — but the agent process may have written the file in
parallel). Decide whether to keep, discard, or finish it. Suggested
action: `git diff --cached -- docs/review-notes/2026-05-06-notification-mixin-dedup.md`
to inspect, then either commit or `git restore --staged --worktree`
the file.

---

## WIP stash status

```text
stash@{0}: On master: preserve-prior-iteration-wip-gt-to-ocr-removal-rebased
```

Untouched all night. This is your prior `gt-to-ocr-removal` work
from before the loop started. The rescue agent in iteration 6 stashed
it after the first iteration's agent left changes uncommitted; every
subsequent iteration was instructed to leave it alone.

When you're ready to triage:

```bash
git stash show stash@{0}            # summary
git stash show stash@{0} -p         # full diff
git stash pop stash@{0}             # restore (may need conflict resolution)
```

---

## Recommended next steps

In rough priority order, items the loop couldn't land without your approval:

1. **Land the GT-input Tab focus fix** (#3 above). One-line change,
   unblocks the queued Tab/Shift+Tab browser test that closes the
   keyboard-shortcut coverage gap.
2. **Investigate `_background_load` stale-closure** (#1 above).
   Real correctness bug; fix is narrow.
3. **Decide on the negative-path Apply test path** (#7 above).
   Either env-var hook (cheap) or accept that unit-level coverage
   suffices.
4. **Triage the stashed WIP** when you have time. It's the largest
   unmerged item in the repo and predates this loop.
5. **Investigate `run.io_bound` `None` return** (#4 above) so the
   iter-31 `retries=100` mitigation can be removed.
6. **Atomic `apply_ocr_config` command** (#2 above). The
   characterization test will tell you when you've got it right.

Other findings (5, 6, 8, 9, 10) are quality-of-life improvements
and can wait.
