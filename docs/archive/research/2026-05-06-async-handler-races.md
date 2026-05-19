# Async Handler Races: Deep Review

Iter 42 / 2026-05-06. Deep review of async-handler patterns in
production code with an eye for stale-closure, mid-await re-render,
exception-swallowing, double-click, and cleanup-on-disconnect race
shapes. Pure documentation; no production or test code changed in
this iter. Successor work is queued in the ranked list at the
bottom.

## Executive summary

Surveyed the async surface in `pd_ocr_labeler/`: 3 `async def
_on_*/_handle_*` handlers, 4 `ui.timer` call sites, ~12 `await
asyncio.sleep(0.1)` checkpoints inside `_action_context` blocks, ~9
`await run.io_bound` call sites, and zero `asyncio.create_task`
direct usages (NiceGUI's `background_tasks.create` is used instead).
The single-handler-per-action serialization that NiceGUI provides
shields most handlers from concurrent re-entrancy, but **two real
bugs** surface: (a) iter-40's previously-documented `input_element.focus()`
attribute error that gets silently swallowed by `ui.timer(0, ...,
once=True)`, and (b) Finding E below — `_background_load`'s post-load
`_update_text_cache(force=True)` reads `self.current_page_index` AFTER
the awaited `run.io_bound` returns, so a fast double-navigate can
populate the text cache for the wrong page. **Three medium-severity
findings** also: (D) export button has no double-click guard;
(F) URL-init timer leaks per session (no `once=True`, no
`active=False` cleanup); (G/I) sync `command_*` calls inside async
handlers block the event loop during pd-book-tools work that should
be `run.io_bound`-wrapped.

## Inventory of async patterns

### `ui.timer` call sites (4)

| File:Line | Interval | `once` | Purpose | Cleanup |
| --- | --- | --- | --- | --- |
| `views/main_view.py:75` | 0.05s | no | drain notification queue | `view._notification_timer.active = False` in `on_disconnect` (`app.py:324-328`) |
| `views/projects/pages/word_match_gt_editing.py:179` | 0s | yes | deferred focus on next GT input after Tab | none needed (one-shot) |
| `views/projects/pages/word_edit_dialog.py:734` | 0s | yes | re-open dialog after split-word index change | none needed (one-shot) |
| `app.py:302` | 0.05s | **no** | start URL initialization once (guarded by `url_init_started` flag) | **none — leaks per session** |

### `await run.io_bound` call sites (9)

| File:Line | Wrapped call | Notes |
| --- | --- | --- |
| `viewmodels/app/app_state_view_model.py:218` | `set_source_projects_root(path)` | OK |
| `app.py:550` | `resolve_project_path(...)` | OK |
| `state/project_state.py:274` | `discover_images_in_directory(...)` | OK |
| `state/project_state.py:290` | `_load_project_from_directory(...)` | OK |
| `state/project_state.py:944` | `get_or_load_page_model(self.current_page_index)` | **Finding E** below |
| `state/project_state.py:1663` | `load_ground_truth_from_directory(...)` | known-flaky `None` return — see priority list item 3 |
| `state/app_state.py:366` | `directory.exists` | OK |
| `viewmodels/project/page_state_view_model.py:207, 479, 496` | various page-model refreshes | OK |

### `await asyncio.sleep(0.1)` checkpoints (~12)

All are inside `_action_context` blocks in `page_view.py` /
`project_view.py` / `export_dialog.py`. Their purpose is to yield the
event loop so the busy-overlay / spinner has a chance to render
before the synchronous backend work begins. **None of them serve as
debouncers** — they do not prevent re-entrancy from a double-click,
because the Click handler is already firing the second invocation
on the next event-loop tick.

### `async def _on_*/_handle_*` (3)

| File:Line | Purpose |
| --- | --- |
| `views/projects/pages/export_dialog.py:99` | scope-radio change → load saved pages |
| `views/projects/pages/export_dialog.py:200` | export button → run export |
| `views/header/project_load_controls.py:337` | source-folder path Enter |

### `background_tasks.create` (3)

| File:Line | Purpose |
| --- | --- |
| `app.py:292, 309` | URL init / CLI auto-load |
| `state/project_state.py:997` | per-page background OCR load |

## Findings

### A — Stale-closure on GT input value-change handler (low)

`views/projects/pages/word_match_gt_editing.py:55-61` —
`input_element.on_value_change(...)` registers a lambda that captures
`word_match.ocr_text` by closure (passed as the `fallback_text`
argument to `_handle_word_gt_input_change`). After a re-render
replaces the underlying `WordMatch` object (via `rerender_line_card`),
the closure still references the old `word_match`. **Impact**:
cosmetic only — the captured fallback OCR text is fed to
`_word_gt_input_width_chars` for monospace width sizing. Wrong width
by a couple of chars is the worst outcome.

### B — Iter-40 focus-method bug (high, already documented)

`views/projects/pages/word_match_gt_editing.py:153` —
`input_element.focus()` raises `AttributeError` because NiceGUI's
`ui.input` does not define `focus`. Wrapped in `ui.timer(0, ...,
once=True)` at line 179, the exception is swallowed silently.
Documented at length in the planning doc at "Real remaining gaps"
item 9 and in
`docs/review-notes/2026-05-06-keyboard-shortcuts-coverage.md` item 1.
Fix sketch: `input_element.run_method("focus")` or
`ui.run_javascript(f"document.querySelector('[data-testid=\"...\"]').focus()")`.
**Out of scope for overnight iters** (production-code change
required, human approval gate).

### C — Mid-await scope-flip race in export dialog `_on_scope_changed` (low)

`views/projects/pages/export_dialog.py:99-131` — handler reads
`self._scope_radio.value` at entry, then `await asyncio.sleep(0.1)`,
then continues. If user flips scope back to `current` during the
100ms yield, the post-await branch still loads pages and notifies
"Loaded N page(s)". The `_pages_loaded = True` flag is set
unconditionally. **Impact**: cosmetic / mildly confusing — pages
were loaded for a scope the user is no longer viewing, but the cache
is correct on its own terms. No data corruption.

### D — Export button has no double-click guard (medium)

`views/projects/pages/export_dialog.py:200-203, 205-256` — neither
`_on_export_clicked` nor `_run_selected_export` checks an
in-progress flag. Compare to `_save_page_async`'s
`if self.project_view_model.is_project_loading:` early-return at
`page_view.py:235`. A user clicking Export twice rapidly would
trigger two concurrent `_run_export` invocations both writing to the
same subfolder. Write order is undefined; the dialog's
results panel will display whichever `_show_results` fires last,
which may be the *first* of two near-simultaneous exports.
**Impact**: stale results displayed; in the worst case, file-system
write conflicts on overlapping subfolders.

**Mitigation pattern**: introduce an `_export_running: bool` instance
flag, set True at `_on_export_clicked` entry inside a try/finally,
return early if already True.

### E — Stale `current_page_index` after `_background_load`'s `run.io_bound` (medium)

`state/project_state.py:927-978` — `_background_load` does:

```python
await run.io_bound(self.get_or_load_page_model, self.current_page_index)  # line 944
self._update_text_cache(force=True)  # line 950
```

`self.current_page_index` is read TWICE: (a) at the synchronous call
site of `run.io_bound` (correct page, the one we're loading), and
(b) implicitly inside `_update_text_cache` after the await returns.
If the user navigates between (a) and (b), the cache update reads a
*different* current page than the one that just loaded. The
post-load logging at lines 967-969 (`_log_page_navigation_timing`)
and 953 (text-cache update) will mismatch the loaded page.

**Impact**: Text Tabs may briefly display content from page N+1
sourced from page N's just-completed OCR, until the next navigation
fires its own `_background_load`. **Reproduction**: navigate fast
enough that two `_navigate(...)` calls fire within the OCR latency
window (multi-second on cold pages). Plausible during keyboard-driven
power-use of Prev/Next.

**Fix sketch**: capture `target_index = self.current_page_index`
before line 944, pass `target_index` explicitly to
`_update_text_cache`, and gate the text-cache update on
`self.current_page_index == target_index` (no-op otherwise — the
later navigation will trigger its own update). The same pattern
should be applied to the `_log_page_navigation_timing` call.

### F — URL-init timer leaks per session (low)

`app.py:302` — `ui.timer(0.05, start_url_initialization)` does NOT
pass `once=True`. After `start_url_initialization` is called once
and `url_init_started = True`, every subsequent 0.05s tick re-enters
the closure, hits `if url_init_started: return`, and does nothing.
The `on_disconnect` handler at `app.py:319-340` clears
`view._notification_timer` (correct) but does not clear this URL-init
timer.

**Impact**: per-session resource leak. NiceGUI's timer machinery
persists in memory past disconnect for sessions that loaded a URL
project. Functionally invisible until enough sessions accumulate.

**Fix sketch**: pass `once=True` to the timer (start_url_initialization
is already idempotent, so `once=True` is the cleaner contract), or
capture the timer handle and call `.active = False` from inside
`start_url_initialization` after firing.

### G — Sync OCR call inside async reload handler (medium)

`views/projects/pages/page_view.py:377, 427` —
`success = self.project_view_model.command_reload_page_with_ocr(...)`
is a synchronous call inside `_reload_ocr_async` /
`_reload_ocr_edited_async`. The call invokes
`_project_state.reload_current_page_with_ocr`, which runs full
detection + recognition OCR via pd-book-tools. This blocks the
asyncio event loop for the entire OCR latency (multi-second on cold
pages). The 0.1s `await asyncio.sleep(0.1)` at line 375 / 425
ensures the spinner overlay paints before the OCR starts, but
nothing yields between OCR start and OCR completion. WebSocket
keepalives, notification timer, and other UI updates all stall.

**Compare**: `state/project_state.py:944` already uses `await
run.io_bound(self.get_or_load_page_model, ...)` for the lazy-load
path. The reload-with-OCR path bypasses that wrapper.

**Fix sketch**: wrap line 377/427 in `await
run.io_bound(self.project_view_model.command_reload_page_with_ocr,
use_edited_image=...)`. Verify ProjectStateViewModel doesn't take a
threading-unsafe shortcut on the synchronous path (it appears not
to — the call delegates straight to `_project_state.reload_*`).

### H — `_handle_word_gt_edit` re-renders during commit (low)

`views/projects/pages/word_match_gt_editing.py:200-235` — after
committing the GT text, the handler calls
`self._view.renderer.rerender_line_card(line_index)` at line 231.
This destroys the inline GT input element that fired the commit and
re-creates a fresh one. The `_word_gt_input_refs` map gets
repopulated. By itself, OK. But combined with **B**, the deferred
`ui.timer(0, lambda: _focus_word_gt_input(target_key), once=True)`
fires AFTER the rerender, so the lookup at line 150 finds the *new*
input element. The focus call still fails (Finding B), but the lookup
itself is sound.

**Impact**: documented in passing here only to confirm the rerender
ordering is safe; the actual bug is Finding B's broken `.focus()`.

### I — Sync `command_save_*` / `command_refine_*` inside async handlers (medium)

`views/projects/pages/page_view.py:243, 267, 294, 320, 346` — all
follow the same pattern: `_action_context` opens the busy overlay,
`await asyncio.sleep(0.1)` lets it paint, then a synchronous
`self.project_view_model.command_*()` call executes the work. Saves
are filesystem I/O (tens to hundreds of ms for pages with many word
images); refines run pd-book-tools layout work (single-second-ish).
All block the event loop while running.

**Severity bucket**: same shape as Finding G but lighter latencies.
Fix is identical: wrap the sync call in `await run.io_bound(...)`.

### J — Load-button double-click guard depends on flag-flip latency (low)

`views/header/project_load_controls.py:204-210` — guard `if
self.project_state_model.is_controls_disabled: return` happens
*before* `await self.app_state_model.command_load_selected_project()`
fires. The `is_controls_disabled` flag isn't flipped until `AppState`
sets `is_project_loading = True` inside `load_selected_project()`,
which is after the await begins. A fast double-click on the LOAD
button could race past the guard if NiceGUI dispatches both clicks
in the same event-loop turn. **Mitigated by**: NiceGUI's per-handler
serialization — in practice clicks are dispatched one at a time,
and by the time the second click reaches the handler, the first has
already started awaiting and the flag is True. Worth a defensive
test (the existing `test_load_button_prevents_multiple_clicks` does
exactly this). **No new finding** — flagged for inventory completeness.

## Coverage matrix: race shape × test coverage

| Race shape | Production site | Test coverage |
| --- | --- | --- |
| Stale closure on word_match | Finding A (`word_match_gt_editing.py:55`) | none — cosmetic only |
| Re-render mid-await | Finding C (`export_dialog.py:115`), Finding E (`project_state.py:944`) | none |
| Exception swallowing in `ui.timer` | Finding B (`word_match_gt_editing.py:153`) | indirect — iter-40 added a negative-path browser test that observes the symptom |
| Double-click guard | Finding D (export), Finding J (load) | `test_load_button_prevents_multiple_clicks` (load only) |
| Sync work in async handler | Finding G, Finding I | none — symptom is "UI freezes for N seconds" which no test asserts |
| Cleanup-on-disconnect | Finding F (URL-init timer) | none — symptom is per-session memory growth |

## Recommended follow-up work, ranked by leverage

1. **Finding E — capture `target_index` before `run.io_bound` in
   `_background_load`.** Single-file production fix with a clear
   correctness motivation. Test sketch: a Python unit test that
   stubs `get_or_load_page_model` to take a configurable delay,
   issues two `_navigate` calls back-to-back, asserts that the
   text-cache update for navigation 1 doesn't fire after navigation
   2 has set `current_page_index`. **Requires production-code
   change — human approval gate.** Defer.
2. **Finding G — wrap reload-with-OCR in `run.io_bound`.** Single-file
   production fix with a UX motivation (UI freezes for the OCR
   duration). Risk: ProjectStateViewModel /
   `_project_state.reload_current_page_with_ocr` might mutate state
   that should remain in the main thread. Pre-flight needed.
   **Requires production-code change.** Defer.
3. **Finding D — add `_export_running` guard to ExportDialog.** Pure
   defensive flag, no behavior change for the common single-click
   path. **Requires production-code change.** Defer.
4. **Finding F — pass `once=True` to URL-init timer at `app.py:302`.**
   One-character functional change but verifies the timer's lifecycle
   contract. **Requires production-code change.** Defer.
5. **Finding I — wrap save-page / save-project / refine-bboxes in
   `run.io_bound`.** Bigger surface (5 sites), each touching a
   different command. Lower per-site UX impact than Finding G.
   **Requires production-code change.** Defer.
6. **Defensive test for Finding C — assert `_pages_loaded` is set
   even if scope flips during the 100ms sleep.** Pure test, no
   production change. Could land overnight but the test surface
   (changing radio value via JS during an awaited handler) is hard
   to drive deterministically in Playwright.
7. **Defensive test that asserts the load-button guard works under
   double-click pressure (Finding J).** Already exists as
   `test_load_button_prevents_multiple_clicks`. No new work.

## Notes for human reviewer

The five medium/low findings that require production-code changes
(B, D, E, F, G, I) all have the same structural shape: a small,
single-file change with a narrow blast radius and a clear contract.
They're each independently mergeable. Finding E is the most urgent
of the bunch — it's a real correctness bug whose user-visible
symptom (wrong page text after fast navigation) has likely been
observed and chalked up to "weird UI glitch."
