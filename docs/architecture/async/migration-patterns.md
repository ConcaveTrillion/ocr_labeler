# NiceGUI Async Migration Patterns

Status: pattern reference for ongoing cleanup and modernization.

Validated against `ocr_labeler/**/*.py` on 2026-02-15.

## Background Task Scheduling

### Before

```python
loop = asyncio.get_running_loop()
task = loop.create_task(some_async_function())
```

### After

```python
from nicegui import background_tasks
background_tasks.create(some_async_function())
```

## IO-Bound Work

### Before

```python
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(executor, blocking_io_function, arg1, arg2)
```

### After

```python
from nicegui import run
result = await run.io_bound(blocking_io_function, arg1, arg2)
```

## File Operations

### Before

```python
await asyncio.to_thread(path.exists)
await asyncio.to_thread(path.read_text, encoding="utf-8")
```

### After

```python
from nicegui import run
await run.io_bound(path.exists)
await run.io_bound(path.read_text, encoding="utf-8")
```

## Notes

- `asyncio.sleep(...)` in async handlers can still be valid when intentionally yielding control.
- Testing should mock NiceGUI async APIs where behavior is asserted.

## Current Codebase Validation

- No usages found for `asyncio.create_task`, `loop.run_in_executor`, `asyncio.to_thread`, or `asyncio.get_running_loop()` in `ocr_labeler/**/*.py`.
- Current runtime scheduling/offload patterns in app code use `background_tasks.create(...)` and `run.io_bound(...)`.
- Current intentional `asyncio` usages are:
	- `asyncio.sleep(...)` in `ocr_labeler/views/projects/project_view.py` for cooperative UI yielding.
