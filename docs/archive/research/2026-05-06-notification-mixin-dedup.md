# Notification mixin dedup deep review (iter 47)

Date: 2026-05-06
Scope: `NotificationMixin._notify` and `_notify_once` semantics, all
call sites, test coverage, dedup correctness risks.

## Executive summary

`NotificationMixin` is a thin facade. `_notify` queues messages
through `AppStateViewModel.queue_notification` (or falls back to
`ui.notify`). `_notify_once(key, ...)` is a per-instance
once-per-lifetime suppression set; it never expires, never clears,
and every owning view holds it for the entire lifetime of the owning
`ProjectView`. Within a project, the mixin is "fire once, never
again" per key. The dedup is concentrated on a small set of
binding/render warnings (six unique keys total), and there is **zero
direct test coverage** of the suppression behavior. The biggest
risks are (a) the same dedup state surviving a project's whole
session even when the underlying transient cause has resolved
(stale-suppression), and (b) divergent twin implementations
(`view_helpers.py`'s `_notify_once` vs `WordMatchView._safe_notify_once`)
that share neither tests nor reset semantics.

## Mixin contract (actual behavior)

`pd_ocr_labeler/views/shared/view_helpers.py:13-46`:

- `_notify(message, type_="info")`:
  - If `self._app_state_view_model is not None`, calls
    `vm.queue_notification(message, type_)` — does NOT call
    `ui.notify` directly. The notification is appended to a deque
    on `AppState`, drained by `LabelerView._flush_queued_notifications`
    on the UI thread (10 per tick).
  - Else falls back to `ui.notify(message, type=type_)`.
  - **No dedup, no rate-limit, no batching.** Two identical messages
    queued back-to-back render as two toasts.
- `_notify_once(key, message, type_="warning")`:
  - Lazily ensures `self._notified_error_keys = set()` via
    `_ensure_notified_keys()`.
  - If `key in keys`, **returns silently — no log, no counter.**
  - Otherwise adds the key and forwards to `_notify`.
  - The key set is **never cleared** anywhere in the codebase.
  - Reset only happens when the mixin instance is garbage-collected
    (i.e., when `ProjectView` is rebuilt — see "Lifecycle" below).

The companion `WordMatchView._safe_notify_once`
(`pd_ocr_labeler/views/projects/pages/word_match.py:213-218`) is a
near-duplicate that reuses the same `_notified_error_keys` attribute
name but goes through `_safe_notify` (which does its own UI-disposal
guard against deleted-client `RuntimeError`). It is **not** the
mixin and has its own copy of the dedup logic.

## Lifecycle of `_notified_error_keys`

| Owner                       | Created in `__init__` | Cleared anywhere | Effective lifetime                    |
|-----------------------------|-----------------------|------------------|---------------------------------------|
| `OCRConfigModal`            | Yes (header)          | No               | Entire NiceGUI session                |
| `ProjectLoadControls`       | Yes (header)          | No               | Entire NiceGUI session                |
| `ProjectNavigationControls` | Yes                   | No               | Per `ProjectView` (rebuilt on switch) |
| `ProjectView`               | Yes                   | No               | Per project switch (see main_view)    |
| `PageActions`               | Yes                   | No               | Per `ProjectView` lifetime            |
| `ImageTabs`                 | Yes                   | No               | Per `ProjectView` lifetime            |
| `WordMatchView`             | Yes (own copy)        | No               | Per `ProjectView` lifetime            |

`LabelerView._handle_state_change` rebuilds `ProjectView` only when
`project_root` changes (`pd_ocr_labeler/views/main_view.py:126-135`),
so within a single project all per-page navigations reuse the same
mixin instance and the same suppression set.

## Call-site inventory (all 6 unique keys)

| File:line                                            | Key                                  | Type   | Trigger                              |
|------------------------------------------------------|--------------------------------------|--------|--------------------------------------|
| `views/projects/pages/image_tabs.py:494`             | `image-tabs-drag-overlay-render`     | warning| Drag-rectangle render exception      |
| `views/projects/pages/image_tabs.py:536`             | `image-tabs-drag-overlay-render`     | warning| Same key reused on a second path     |
| `views/projects/pages/image_tabs.py:670`             | `image-tabs-drag-overlay-clear`      | warning| Drag-rectangle clear exception       |
| `views/projects/pages/image_tabs.py:1022`            | `image-tabs-geometry-{tab}`          | warning| Image geometry update per tab        |
| `views/projects/pages/word_edit_dialog.py:112`       | `word-split-marker-render`           | warning| Split-marker overlay render exception|
| `views/projects/pages/word_match_renderer.py:888`    | `word-image-render`                  | warning| Per-word PIL render exception        |
| `views/projects/pages/word_match_gt_editing.py:480`  | `word-style-button-refresh`          | warning| Style-button bind exception          |
| `view_helpers.py:71,94,117` (`_bind_*_safe`)         | caller-supplied                      | warning| Generic `binding.bind*` exceptions   |

Note: `image_tabs.py:494` and `:536` deliberately share
`"image-tabs-drag-overlay-render"`; first failure suppresses both.

## `_notify` (no-dedup) call sites — sample

`grep -n "_notify(" pd_ocr_labeler/` shows ~45 call sites. The vast
majority are one-shot user actions where dedup is unnecessary
(export progress, dialog confirmations, etc.). High-volume callers
worth flagging:

- `state/project_state.py:604,622,679,706,815` — loading-status
  pumps. These run inside async loops and will queue identical
  `loading_status` strings repeatedly; the queue layer has no
  string-equality coalescing. Browser users see toast spam during
  long loads.
- `views/projects/pages/text_tabs.py:341` and
  `views/projects/pages/page_view.py:203` — direct
  `queue_notification` bypassing the mixin entirely.

## Test coverage matrix

| Behavior under test                                 | Asserted?   | Where                                                        |
|-----------------------------------------------------|-------------|--------------------------------------------------------------|
| `_notify` forwards to `vm.queue_notification`       | Indirect    | iter 44/45/46 unit tests via stub                            |
| `_notify` falls back to `ui.notify` when vm is None | No          | —                                                            |
| `_notify_once` emits the first time                 | No (direct) | —                                                            |
| `_notify_once` suppresses the second time           | **No**      | —                                                            |
| `_notify_once` is per-instance (two views isolated) | **No**      | —                                                            |
| `_notify_once` survives navigation within a project | **No**      | —                                                            |
| `_notify_once` resets across project switch         | **No**      | —                                                            |
| `_safe_notify_once` parity with `_notify_once`      | **No**      | —                                                            |
| Notification queue drains on `LabelerView` timer    | Indirect    | `tests/.../test_app_url_loading.py` exercises queue contents |

`grep -rn "_notify_once\|_safe_notify_once\|notified_error_keys" tests/`
returns no hits.

## Notable findings

### F1 — Duplicate of dedup logic, no shared contract (medium)

`WordMatchView._safe_notify_once`
(`word_match.py:213-218`) is byte-for-byte equivalent to
`NotificationMixin._notify_once` but lives on a class that
**deliberately is not a `NotificationMixin` subclass.** Both
implementations name their state attribute `_notified_error_keys`,
so a future refactor that mixes one into the other will see
attribute collision. There is no test pinning either contract.
Recommendation: have `WordMatchView` inherit from `NotificationMixin`
and delete the duplicate, or extract a free function shared by
both.

### F2 — Stale suppression across long sessions (medium)

`_notified_error_keys` is never cleared. For users who switch
between pages (no project switch) all session long, a single
transient render failure on page 3 (e.g., a momentarily missing
image file later restored) silently suppresses the warning for
every subsequent page. Concrete code path:
`image_tabs.py:1022` fires once on a flaky image, then the user
fixes the file and navigates to other pages where the same flaky
condition would still warn — but it does not. Recommendation: either
expire keys on a TTL or reset them on page navigation.

### F3 — Loading-status toast spam (low/medium)

`project_state.py:604,622,679,706` re-queue
`self.loading_status` after every batch step. With long projects
this produces multiple identical "Loading page N of M" toasts that
users have to dismiss. The state-side `queue_notification` does no
collapsing (`app_state.py:104` and `project_state.py:114`); it simply
appends. Recommendation: either coalesce equal head-of-queue
messages on enqueue, or use the loading_status field via a
reactive label rather than a toast.

### F4 — `_ensure_notified_keys` is dead code in practice (cosmetic)

Every concrete subclass already initializes
`self._notified_error_keys: set[str] = set()` in `__init__`
(see `image_tabs.py:109`, `word_match.py:193`, etc.).
`_ensure_notified_keys` (`view_helpers.py:25-28`) only fires when
the subclass forgot — but the class annotation
`_notified_error_keys: set[str]` (line 23) without a default makes
forgetting a hard error on attribute access *before* the
`hasattr` guard would help. Net effect: the lazy init is defensive
dead code; can be removed once a test pins the invariant.

### F5 — `_notify` ignores `_notified_error_keys` (by design — flag for clarity)

`_notify` and `_notify_once` share state only through the keys
set; `_notify` will happily emit a message that has the same text
as a previously-suppressed `_notify_once` message. Two call sites
in `image_tabs.py` (the geometry-update branch around lines 1022
and the drag-overlay branches) split between the two methods, so
under back-to-back failures the user can see the warning fire from
the `_notify` site even though the `_notify_once` site is silenced.
Not a bug; documenting because future maintainers may assume
otherwise.

## Ranked follow-up work

1. **(highest leverage)** Add a 4-test unit suite for
   `NotificationMixin._notify_once` covering: emits-first,
   suppresses-second, distinct-keys-independent, distinct-instances-
   independent. Pure dataclass test, no NiceGUI runtime needed.
   ~40 lines. Pins F1/F2/F4 behaviorally and protects future
   refactors.
2. Add 2 tests for `_notify` fallback path (vm-None vs vm-set),
   asserting `ui.notify` is called only in the former. Already
   easy with the stub pattern from iter 44/45.
3. Decide on F2: TTL or page-nav reset. If reset, do it as a small
   `reset_notification_dedup()` method on the mixin called from
   `PageView.refresh` after a page-index change.
4. Consider deleting `_safe_notify_once` from `WordMatchView` and
   making it inherit `NotificationMixin` (F1). Behavioral parity:
   yes (modulo `_safe_notify` UI-disposal guard, which can be
   pulled into the mixin).
5. Coalesce identical loading-status enqueues in
   `state/{app,project}_state.py:queue_notification` (F3). One-liner:
   if the deque is non-empty and the tail equals `(message, kind)`,
   skip the append.

## Files surveyed

- `pd_ocr_labeler/views/shared/view_helpers.py`
- `pd_ocr_labeler/viewmodels/app/app_state_view_model.py`
- `pd_ocr_labeler/state/app_state.py`
- `pd_ocr_labeler/state/project_state.py`
- `pd_ocr_labeler/views/main_view.py`
- `pd_ocr_labeler/views/projects/project_view.py`
- `pd_ocr_labeler/views/projects/pages/page_view.py`
- `pd_ocr_labeler/views/projects/pages/content.py`
- `pd_ocr_labeler/views/projects/pages/image_tabs.py`
- `pd_ocr_labeler/views/projects/pages/word_match.py`
- `pd_ocr_labeler/views/projects/pages/word_match_gt_editing.py`
- `pd_ocr_labeler/views/projects/pages/word_match_renderer.py`
- `pd_ocr_labeler/views/projects/pages/word_edit_dialog.py`
- `pd_ocr_labeler/views/header/ocr_config_modal.py`
- `pd_ocr_labeler/views/header/project_load_controls.py`
- `tests/` (grep audit only — no edits)
