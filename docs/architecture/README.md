# Architecture Docs

Architecture documentation is organized into smaller, topic-focused files.

Status: maintained incrementally; validate details against current implementation.

Last validated: 2026-04-16.

## Current Code Map (2026-04-16 snapshot)

- App entry and routing:
  - `ocr_labeler/app.py`
  - `ocr_labeler/routing.py`
  - `ocr_labeler/cli.py`
  - `ocr_labeler/local_state_cleanup.py`
- Models:
  - `ocr_labeler/models/project_model.py`
  - `ocr_labeler/models/page_model.py`
  - `ocr_labeler/models/word_match_model.py`
  - `ocr_labeler/models/line_match_model.py`
  - `ocr_labeler/models/user_page_persistence.py`
- State layer:
  - `ocr_labeler/state/app_state.py`
  - `ocr_labeler/state/project_state.py`
  - `ocr_labeler/state/page_state.py`
- ViewModel layer:
  - `ocr_labeler/viewmodels/main_view_model.py`
  - `ocr_labeler/viewmodels/shared/base_viewmodel.py`
  - `ocr_labeler/viewmodels/app/app_state_view_model.py`
  - `ocr_labeler/viewmodels/project/project_state_view_model.py`
  - `ocr_labeler/viewmodels/project/page_state_view_model.py`
  - `ocr_labeler/viewmodels/project/word_match_view_model.py`
- View layer:
  - `ocr_labeler/views/main_view.py`
  - `ocr_labeler/views/callbacks.py`
  - `ocr_labeler/views/header/{header,project_load_controls}.py`
  - `ocr_labeler/views/projects/{project_view,project_navigation_controls}.py`
  - `ocr_labeler/views/projects/pages/{page_view,page_actions,content,image_tabs,text_tabs}.py`
  - `ocr_labeler/views/projects/pages/{word_match,word_match_toolbar,word_match_renderer,word_match_selection,word_match_actions,word_match_bbox,word_match_gt_editing}.py`
  - `ocr_labeler/views/projects/pages/{word_edit_dialog,word_operations,export_dialog}.py`
  - `ocr_labeler/views/shared/{base_view,button_styles}.py`
- Operations:
  - `ocr_labeler/operations/ocr/{navigation_operations,page_operations,text_operations,line_operations,word_operations,ocr_service}.py`
  - `ocr_labeler/operations/persistence/{config_operations,persistence_paths_operations,project_discovery_operations,project_operations}.py`
  - `ocr_labeler/operations/export/{doctr_export,cli}.py`
  - `ocr_labeler/operations/validation/` (placeholder — not yet implemented)
- Services:
  - `ocr_labeler/services/notification_service.py`

Use this map as the first checkpoint when reconciling architecture docs with implementation.

## Naming Conventions

- Use `*_view_model` naming for ViewModel modules, symbols, and attributes.
- Keep `PageStateViewModel` in the ViewModel layer only: `ocr_labeler/viewmodels/project/page_state_view_model.py`.
- Do not place ViewModel classes under `ocr_labeler/models/`.

## Multi-Tab Session Isolation

- [Overview](multi-tab/overview.md)
- [State Hierarchy](multi-tab/state-hierarchy.md)
- [Pitfalls and Debugging](multi-tab/pitfalls-and-debugging.md)

## NiceGUI Async Architecture

- [Overview](async/overview.md)
- [Migration Patterns](async/migration-patterns.md)
- [Affected Files and Notes](async/affected-files.md)

## NiceGUI Usage Patterns

- [Patterns and Guardrails](nicegui-patterns.md)

## External Model Alignment

- [pd-book-tools Model Alignment](pd-book-tools-model-alignment.md)

## Threading Notes

- [Threading Architecture](threading-architecture.md)

## Doc Sync Tasks

- [Architecture Doc Sync Tasks](doc-sync-tasks.md)
