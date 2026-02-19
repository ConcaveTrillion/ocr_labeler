# Threading Architecture for OCR Processing

This document captures the current threading/offload model for OCR-related work in the UI.

Status: validated against current code on 2026-02-18.

## Principle

Keep expensive OCR and filesystem operations off the main NiceGUI event loop.

## Preferred Execution Model

- Use `run.io_bound(...)` for blocking I/O.
- Use `run.cpu_bound(...)` when CPU-bound process isolation is appropriate (not currently used in app package).
- Use `background_tasks.create(...)` for fire-and-forget async orchestration.

## Current Call Paths

- Project load path:
	- `ProjectState.load_project(...)` uses `run.io_bound(...)` for directory scan and project creation.
	- `ProjectState.load_ground_truth_map(...)` uses `run.io_bound(...)` for filesystem and JSON parsing.
- Navigation path:
	- `ProjectState._navigate()` sets navigation flags and schedules `_background_load()` via `background_tasks.create(...)`.
	- `_background_load()` preloads target page via `await run.io_bound(self.get_page, ...)`.
- Image refresh path:
	- `PageStateViewModel._schedule_image_update()` schedules async update via `background_tasks.create(...)`.
	- `_update_image_sources_async()` uses `run.io_bound(...)` for image refresh and encoding work.

## Runtime Notes

- A blocking fallback path exists for no-event-loop/test contexts in some components; production paths are async (`background_tasks.create` + `run.io_bound`).
- No current `run.cpu_bound(...)` call sites were found in `ocr_labeler/**/*.py` during this validation pass.

## Design Goals

- Maintain websocket responsiveness during OCR/navigation.
- Avoid event-loop starvation from blocking calls.
- Keep UI status updates reactive and non-blocking.

## Related Docs

- [Async Overview](async/overview.md)
- [Migration Patterns](async/migration-patterns.md)
- [Affected Files and Notes](async/affected-files.md)
