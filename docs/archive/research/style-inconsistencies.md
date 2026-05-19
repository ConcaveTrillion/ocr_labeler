# Style Inconsistencies

Issues with naming conventions, type annotations, logging patterns, and
structural patterns found across the codebase.

## Typing: `Optional[X]` vs `X | None`

All files import `from __future__ import annotations`, making modern union
syntax available everywhere. Usage is inconsistent:

- **Mixed files**: `app_state.py`, `page_state.py`, `project_state.py`,
  `user_page_persistence.py`, `app_state_view_model.py`
- **Old-style collections**: `line_match_model.py`, `text_operations.py`,
  `project_discovery_operations.py`, `base_viewmodel.py` use `List[X]`,
  `Dict[X,Y]`, `Tuple[X,Y]`
- **Old-style Callable**: `navigation_operations.py` uses
  `typing.Callable` instead of `collections.abc.Callable`

## Logging

### f-string in logger calls

f-strings evaluate eagerly even when the log level is disabled. Found in
20+ locations:

- `app_state.py` L113
- `app.py` L218, L222, L282, L310, L319, L330, L546
- `project_operations.py` L116, L119, L147, L150, L158
- `base_viewmodel.py` L76
- `notification_service.py` throughout
- `routing.py` L90, L112
- Multiple view files

**Fix**: Use `%s`-style formatting: `logger.info("Loaded %s", path)`.

### Redundant `{e}` in `logger.exception()`

`logger.exception()` already includes the traceback.
`logger.exception(f"Error: {e}")` logs `e` twice. Found in many files.

### Logger import style

Two competing patterns:

- **Standard** (most files):
  `import logging; logger = logging.getLogger(__name__)`
- **Non-standard** (`base_viewmodel.py` L9, `base_view.py` L9):
  `logger = __import__("logging").getLogger(__name__)`

### Logger severity misuse

- `logger.critical` for "no page available" guard conditions in
  `project_state.py` — should be `logger.warning`
- `logger.warning` for "already at first page" boundary in
  `navigation_operations.py` — should be `logger.debug`

## Methods vs Properties

- `project_model.py`: `page_count()` is a method but has no side effects
  and returns a simple derived value — should be `@property`

## Return Type Annotations

- `line_operations.py` L438: `dict[str, any]` — lowercase `any` is the
  builtin function, not `typing.Any`. **This is a bug.**
- `cli.py`: `parse_args()` and `get_logging_configuration()` lack return
  type annotations.

## Static vs Instance Methods

- `ConfigOperations`, `ProjectDiscoveryOperations`,
  `SessionStateOperations` use `@staticmethod`/`@classmethod`
- `ProjectOperations` uses instance methods despite having no instance
  state — inconsistent
- `TextOperations` is all `@staticmethod` — effectively a namespace for
  utility functions

## `notify()` Error Handling

- `AppState.notify()` — **no** per-listener error handling
- `ProjectState.notify()` — **no** per-listener error handling
- `PageState.notify()` — **has** try/except per listener

Should be consistent across all state classes.

## Error Handling Return vs Re-raise

- Most structural editing methods in `PageState` catch exceptions and
  `return False`
- `nudge_word_bbox()` catches, logs, then **re-raises** — different
  pattern from all siblings

## Inline Imports

Deferred imports inside method bodies, sometimes unnecessarily:

- `import traceback` inside except: `word_match_model.py` L124,
  `line_match_model.py` L201
- `import datetime` inside method: `project_operations.py` L200
- `import threading` inside method: `project_view.py` L178
- `from pathlib import Path` inside method:
  `app_state_view_model.py` L155

## `WordOperations()` Instantiation

`WordOperations()` is stateless but instantiated on every call in
`word_match.py` L541 (`_word_style_flags` per word per render). Should be
a class-level or module-level constant.

## `_is_disposed_ui_error` Duplicated Helper

The same helper method appears in:

- `word_match.py` L221
- `text_tabs.py` L877

Should be shared in `views/shared/`.

## `_notified_error_keys` Never Cleared

In `image_tabs.py` L110 and `page_actions.py` L56,
`_notified_error_keys: set[str]` accumulates forever. If an error
resolves and recurs, the user won't see a second notification.

## Ad-hoc Attribute on Dataclass

`page_state.py` L2520: `_current_page_index` property uses
`getattr(self, "_page_index", 0)` — ad-hoc attribute on a `@dataclass`
not declared as a field. Should be
`_page_index: int = field(default=0, init=False)`.
