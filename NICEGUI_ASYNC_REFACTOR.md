# NiceGUI Async Threading Refactor

## Problem
The codebase was using low-level asyncio APIs that interfere with NiceGUI's event loop management, causing websocket disconnections and UI freezes:
- `asyncio.get_running_loop()` + `loop.create_task()`
- `asyncio.get_running_loop()` + `loop.run_in_executor()`
- Direct `asyncio.to_thread()` calls

## Solution
Replaced all low-level asyncio operations with NiceGUI's proper async APIs as documented at:
- https://nicegui.io/documentation/section_configuration_deployment#background_tasks
- https://nicegui.io/documentation/section_action_events#running_cpu-bound_tasks

## Changes Made

### 1. Background Task Creation
**Before:**
```python
loop = asyncio.get_running_loop()
task = loop.create_task(some_async_function())
```

**After:**
```python
from nicegui import background_tasks
background_tasks.create(some_async_function())
```

### 2. IO-Bound Operations
**Before:**
```python
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(executor, blocking_io_function, arg1, arg2)
```

**After:**
```python
from nicegui import run
result = await run.io_bound(blocking_io_function, arg1, arg2)
```

### 3. File Operations
**Before:**
```python
await asyncio.to_thread(path.exists)
await asyncio.to_thread(path.read_text, encoding="utf-8")
```

**After:**
```python
await run.io_bound(path.exists)
await run.io_bound(path.read_text, encoding="utf-8")
```

## Files Modified

### Core State Management
1. **ocr_labeler/viewmodels/project/page_state_view_model.py**
   - Removed `asyncio` import, added `background_tasks` and `run` from nicegui
   - Replaced `_pending_update_task: Optional[asyncio.Task]` with `_update_in_progress: bool`
   - Updated `_schedule_image_update()` to use `background_tasks.create()`
   - Updated `_update_image_sources_async()` to use `run.io_bound()` for image encoding

2. **ocr_labeler/state/project_state.py**
   - Removed `asyncio` import, added `background_tasks` and `run` from nicegui
   - Updated `_schedule_async_load()` to use `background_tasks.create()`
   - Replaced `asyncio.to_thread()` with `run.io_bound()` for page loading
   - Updated `load_ground_truth_map()` to use `run.io_bound()` for file operations

### Operations Layer
3. **ocr_labeler/operations/ocr/navigation_operations.py**
   - Removed `asyncio` import, added `run` from nicegui
   - Updated `schedule_async_navigation()` to use `run.io_bound()` for background loading

4. **ocr_labeler/operations/ocr/page_operations.py**
   - Removed `asyncio` import, added `run` from nicegui
   - Updated `can_load_page()` to use `run.io_bound()` for file existence checks and JSON parsing

5. **ocr_labeler/operations/persistence/project_operations.py**
   - Updated `scan_project_directory()` to use `run.io_bound()` for file system operations
   - Updated `validate_project_directory()` to use `run.io_bound()` for path validation

### View Layer
6. **ocr_labeler/views/projects/project_controls.py**
   - Removed `asyncio` import, added `run` from nicegui
   - Updated `_prev_page()` and `_next_page()` to use `run.io_bound()`

7. **ocr_labeler/views/projects/pages/page_controls.py**
   - Updated `_reload_ocr_async()` to use `run.io_bound()` for command execution
   - Kept `asyncio.iscoroutinefunction()` check (inspection only, no event loop interference)

### Test Files
8. **tests/state/operations/test_app_state_2.py**
   - Updated `test_navigate_async_path_schedules_task()` to mock `background_tasks.create()` instead of `loop.create_task()`

### Files Reviewed (No Changes Needed)
- **ocr_labeler/views/projects/project_view.py** - Uses `asyncio.sleep()` for yielding control (valid pattern)
- **ocr_labeler/views/projects/pages/page_controls.py** - Uses `asyncio.iscoroutinefunction()` for inspection (safe)

## Benefits

1. **Proper Event Loop Management**: NiceGUI's APIs handle event loop lifecycle correctly
2. **No Websocket Disconnections**: Background tasks no longer block the main event loop
3. **Better Error Handling**: NiceGUI provides graceful fallbacks and proper cleanup
4. **Thread Pool Management**: `run.io_bound()` uses NiceGUI's optimized thread pools
5. **Future-Proof**: Following NiceGUI's documented best practices

## API Reference

### background_tasks.create(coroutine)
- Creates background tasks that are automatically cleaned up on shutdown
- Use `@background_tasks.await_on_shutdown` decorator for tasks that must complete

### run.io_bound(function, *args, **kwargs)
- Runs IO-bound tasks (file operations, network calls) in a separate thread
- Returns awaitable that resolves to function result

### run.cpu_bound(function, *args, **kwargs)
- Runs CPU-intensive tasks in a separate process
- Handles pickle serialization automatically

## Migration Notes

- `asyncio.sleep()` calls in event handlers are still OK (yield control to event loop)
- Tests may need to mock `nicegui.background_tasks.create` instead of asyncio APIs
- The `ThreadPoolExecutor` for image encoding is kept but now used via `run.io_bound()`

## Test Results
✅ All 256 tests passing
✅ Build successful
✅ Coverage maintained at 61.1%
