# NiceGUI Patterns & Guardrails

Project-specific NiceGUI patterns for consistent UI behavior.

Status: active guidance.

Last validated: 2026-02-18.

## Core Principles

- Build UI with composable views and explicit `build()` boundaries.
- Keep state and view concerns separate (ViewModel drives UI state).
- Preserve per-session isolation (state/viewmodel/view are created per route/session).

## Naming

- Use canonical `*_view_model` names in code.
- Prefer `*_view_model` attribute names (for example, `project_state_view_model`).

See also:
- `multi-tab/overview.md`
- `multi-tab/state-hierarchy.md`

## Reactive Binding Patterns

- Use bindable ViewModel state (`@binding.bindable_dataclass`) for reactive properties.
- Prefer one-way binding for display-only state (`bind_from` / `bind_*_from`).
- Use two-way binding only for editable controls that are intended to mutate state.

### Image Source Caveat

Do not rely on direct binding of image source for page image updates. Prefer explicit callback/update methods (`set_source(...)`) triggered by relevant property changes.

## Async Execution Patterns

- Use `run.io_bound(...)` for blocking file/OCR/image encoding operations.
- Use `background_tasks.create(...)` for fire-and-forget async orchestration.
- Keep async handlers (`async def`) lightweight and update UI state before/after long operations.

Avoid raw asyncio scheduling/offload patterns in app code:
- `asyncio.create_task(...)`
- `loop.run_in_executor(...)`
- `asyncio.to_thread(...)`

Detailed migration examples live in:
- `async/overview.md`
- `async/migration-patterns.md`
- `async/affected-files.md`

## UX & Reliability Expectations

- Show loading/working state for long operations.
- Avoid blocking the event loop with synchronous heavy work.
- Register disconnect/session cleanup where resources or listeners are retained.
- Use `ui.notify(...)` for user-visible success/error feedback on async actions.

## When Updating This Doc

- Keep patterns implementation-oriented and brief.
- Link to canonical architecture docs instead of duplicating large code examples.
- Update `docs/architecture/README.md` when adding or renaming related docs.
