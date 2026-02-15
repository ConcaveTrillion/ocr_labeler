# NiceGUI Async Refactor: Affected Files and Notes

Status: living inventory; keep updated as async call paths change.

Last validated: 2026-02-15.

## State and ViewModels

- `ocr_labeler/state/page_state.py`
- `ocr_labeler/state/project_state.py`
- `ocr_labeler/viewmodels/project/page_state_view_model.py`
- `ocr_labeler/viewmodels/project/project_state_view_model.py`

## Operations

- `ocr_labeler/operations/ocr/navigation_operations.py`
- `ocr_labeler/operations/ocr/page_operations.py`
- `ocr_labeler/operations/ocr/text_operations.py`
- `ocr_labeler/operations/ocr/ocr_service.py`
- `ocr_labeler/operations/persistence/project_operations.py`

## Views

- `ocr_labeler/views/main_view.py`
- `ocr_labeler/views/projects/project_view.py`
- `ocr_labeler/views/projects/project_controls.py`
- `ocr_labeler/views/projects/pages/page_controls.py`
- `ocr_labeler/views/projects/pages/content.py`
- `ocr_labeler/views/projects/pages/image_tabs.py`
- `ocr_labeler/views/projects/pages/text_tabs.py`
- `ocr_labeler/views/projects/pages/word_match.py`

## Tests

- `tests/state/operations/test_app_state_2.py`
- `tests/state/operations/test_line_operations.py`

## Migration Caveat

File-level and API-level details in these notes are snapshots and should be treated as guidance until revalidated against current code.
