# Threading Architecture for OCR Processing

## Overview

The OCR Labeler application uses asynchronous programming and thread pools to ensure that long-running OCR operations do not block the UI or websocket connection. This document explains how the threading works and verifies that OCR processing happens in separate threads.

## Key Architecture Components

### 1. Async/Await Pattern with NiceGUI

NiceGUI runs on top of an asyncio event loop, which handles:
- WebSocket communication with the browser
- UI updates and rendering
- Event handling (button clicks, navigation, etc.)

**Critical requirement**: Never block the asyncio event loop with CPU-intensive or I/O-bound operations, as this will freeze the UI and potentially disconnect the websocket.

### 2. Thread Pool Execution for OCR

All OCR processing is delegated to a separate thread pool using `asyncio.to_thread()`. This ensures:
- The asyncio event loop remains responsive
- WebSocket connections stay alive
- UI updates continue to work
- Multiple OCR operations can run concurrently without blocking each other

## Navigation Flow with Threading

### Typical Page Navigation Sequence

1. **User clicks "Next" button** (in browser)
   - Event fires in NiceGUI event loop
   - `project_view._next_async()` is called (async coroutine)

2. **Navigation initiated** (main thread, event loop)
   - `ProjectStateViewModel.command_navigate_next()` is called
   - `ProjectState.next_page()` updates the page index
   - `ProjectState._navigate()` is called

3. **Background loading scheduled** (main thread, event loop)
   - `ProjectState._navigate()` sets `is_navigating = True`
   - Creates coroutine `_background_load()`
   - Schedules it with `loop.create_task()`
   - **Returns immediately** - does not block!

4. **Page loading in thread pool** (separate worker thread)
   - `asyncio.to_thread(self.get_page, self.current_page_index)` executes
   - `get_page()` -> `ensure_page()` runs in thread pool
   - OCR processing via DocTR happens in this thread
   - No impact on event loop or websocket

5. **UI updates** (main thread, event loop)
   - `loading_status` property updates trigger UI refresh
   - Status messages appear: "Checking for saved page...", "Running OCR...", etc.
   - Spinner shows while loading
   - UI remains fully responsive

6. **Completion** (main thread, event loop)
   - Thread pool work completes
   - Event loop resumes the coroutine
   - `is_navigating = False`
   - Final UI update with loaded page content

## Code Verification Points

### ProjectState._navigate() (state/project_state.py)

```python
async def _background_load():
    try:
        # PRE-LOAD in THREAD POOL - prevents blocking event loop
        await asyncio.to_thread(self.get_page, self.current_page_index)
        # Update text cache now that page is loaded
        self._update_text_cache(force=True)
        self.loading_status = "Page loaded successfully"
    finally:
        self.is_navigating = False
        await asyncio.sleep(0.5)
        self.loading_status = ""
        self.notify()
```

**Key point**: `asyncio.to_thread()` runs `self.get_page()` in a thread pool worker, not in the event loop thread.

### ProjectState.ensure_page() (state/project_state.py)

This method is called from within the thread pool (via `to_thread`). It performs:
- File I/O (checking for saved pages)
- OCR processing via DocTR (CPU-intensive)
- Ground truth text injection

**Verification**: All status updates call `self.notify()`, which safely schedules UI updates in the event loop. The OCR work itself happens synchronously in the worker thread.

### PageOperations.build_initial_page_parser() (operations/ocr/page_operations.py)

```python
def _parse_page(path: Path, index: int, ground_truth_string: str) -> Page:
    from pd_book_tools.ocr.document import Document

    predictor = self._get_or_create_predictor()
    # DocTR OCR runs HERE - in the thread pool worker
    doc = Document.from_image_ocr_via_doctr(
        path,
        source_identifier=path.name,
        predictor=predictor,
    )
    page_obj: Page = doc.pages[0]

    if ground_truth_string:
        page_obj.add_ground_truth(ground_truth_string)

    return page_obj
```

**Verification**: This function is called from `ensure_page()`, which runs in the thread pool via `asyncio.to_thread()`.

## Status Message Flow

During navigation, the user sees these status messages in real-time:

1. **"Navigating to next page (OCR may run in background)..."**
   - Initial notification when navigation starts
   - Shows in the action overlay

2. **"Checking for saved page..."**
   - Appears in the status label as soon as directory check begins
   - Updated via `ProjectState.loading_status`

3. **"Loading page from disk..."**
   - If a saved page is found
   - Shows the page is being deserialized from JSON

4. **"Running OCR on page (in background thread)..."**
   - If OCR is needed (no saved page found)
   - Explicitly indicates threading to reassure user
   - OCR processing happens during this status

5. **Success notification** (modal popup)
   - "Navigated to next/previous page" or "Navigated to page N"
   - Shows as a green notification toast
   - Appears when navigation command succeeds
   - Disappears automatically after a few seconds

6. **(empty status)**
   - Status label clears when page load completes
   - UI returns to normal state

## WebSocket Safety

### Why This Matters

NiceGUI uses WebSockets for real-time communication between the Python backend and browser frontend. If the backend event loop blocks for too long:
- WebSocket ping/pong timeouts can occur
- Connection may be terminated by browser or server
- UI becomes unresponsive
- User may see "Disconnected" or "Reconnecting" messages

### How We Prevent Blocking

1. **All OCR work in thread pools**: `asyncio.to_thread()` ensures OCR never blocks the event loop
2. **Short async sleeps**: `await asyncio.sleep(0.1)` allows event loop to process other events
3. **Reactive UI updates**: Status changes trigger bindings, not polling
4. **Background task scheduling**: `create_task()` schedules work without waiting

### Testing Thread Safety

To verify threading works correctly:

1. **Enable verbose logging**: Run with `--verbose` flag to see thread IDs in logs
2. **Monitor event loop**: Watch for warnings about slow callbacks
3. **Test long OCR**: Navigate through many pages rapidly - UI should stay responsive
4. **Network latency**: Test with slow network - websocket should remain connected
5. **Browser DevTools**: Check WebSocket tab for connection stability

## Fallback Behavior

If no event loop is running (e.g., during testing), the code falls back to synchronous operation:

```python
try:
    loop = asyncio.get_running_loop()
except RuntimeError:  # no running loop at all
    logger.info("No running event loop; falling back to synchronous page load")
    # Fallback synchronous load
    try:
        self.get_page(self.current_page_index)
    finally:
        self.is_project_loading = False
        self.is_navigating = False
        self.notify()
    return
```

This ensures the application works in both production (with event loop) and tests (without).

## Summary

✅ **OCR processing runs in separate threads** via `asyncio.to_thread()`
✅ **Event loop never blocks** - always responsive
✅ **WebSocket connections remain stable** - no timeouts
✅ **UI updates reactively** - status messages update in real-time
✅ **Graceful degradation** - fallback for non-async environments

The architecture ensures a smooth, responsive user experience even during CPU-intensive OCR operations.
