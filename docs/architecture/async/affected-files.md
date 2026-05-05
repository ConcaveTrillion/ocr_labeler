# NiceGUI Async Refactor: Affected Files and Notes

Status: living inventory; keep updated as async call paths change.

Last validated: 2026-05-05.

## State and ViewModels

- `pd_ocr_labeler/state/page_state.py`
- `pd_ocr_labeler/state/project_state.py`
- `pd_ocr_labeler/viewmodels/project/page_state_view_model.py`
- `pd_ocr_labeler/viewmodels/project/project_state_view_model.py`

## Operations

- `pd_ocr_labeler/operations/ocr/navigation_operations.py`
- `pd_ocr_labeler/operations/ocr/page_operations.py` — note: now performs
  lazy Hugging Face weight downloads via `pd_book_tools.hf.hf_download`
  on first OCR call when configured with `HuggingFaceWeightsDescriptor`s.
  Treat the first `_get_or_create_predictor()` invocation per session as
  blocking I/O even when local files are present (sidecar resolution
  still touches disk).
- `pd_ocr_labeler/operations/ocr/text_operations.py`
- `pd_ocr_labeler/operations/ocr/ocr_service.py`
- `pd_ocr_labeler/operations/ocr/image_cache_operations.py` — JPEG/PNG
  encode + `Path.write_bytes` per page on cache miss; called from page
  load path and should run via `run.io_bound` when invoked from request
  handlers.
- `pd_ocr_labeler/operations/persistence/project_operations.py`
- `pd_ocr_labeler/operations/export/doctr_export.py` — JSON read/write
  and image copies during DocTR-format export; the `pd-ocr-labeler-export`
  CLI is synchronous, but UI-driven export must dispatch via
  `run.io_bound` or `background_tasks.create` to avoid blocking the
  event loop.
- `pd_ocr_labeler/operations/export/cli.py` — entry point for the
  `pd-ocr-labeler-export` console script (synchronous; no event loop).

## Views

- `pd_ocr_labeler/views/main_view.py`
- `pd_ocr_labeler/views/projects/project_view.py`
- `pd_ocr_labeler/views/projects/project_navigation_controls.py`
- `pd_ocr_labeler/views/projects/pages/page_view.py`
- `pd_ocr_labeler/views/projects/pages/page_actions.py`
- `pd_ocr_labeler/views/projects/pages/content.py`
- `pd_ocr_labeler/views/projects/pages/image_tabs.py`
- `pd_ocr_labeler/views/projects/pages/text_tabs.py`
- `pd_ocr_labeler/views/projects/pages/word_match.py`

## Tests

- `tests/state/operations/test_app_state_2.py`
- `tests/state/operations/test_line_operations.py`

## Migration Caveat

File-level and API-level details in these notes are snapshots and should be
treated as guidance until revalidated against current code.
