# Architecture Docs

Architecture documentation is organized into smaller, topic-focused files.

Status: maintained incrementally; validate details against current implementation.

Last validated: 2026-02-15.

## Current Code Map (2026-02 snapshot)

- App entry and routing:
	- `ocr_labeler/app.py`
	- `ocr_labeler/routing.py`
	- `ocr_labeler/cli.py`
- State layer:
	- `ocr_labeler/state/app_state.py`
	- `ocr_labeler/state/project_state.py`
	- `ocr_labeler/state/page_state.py`
- ViewModel layer:
	- `ocr_labeler/viewmodels/main_view_model.py`
	- `ocr_labeler/viewmodels/app/app_state_view_model.py`
	- `ocr_labeler/viewmodels/project/project_state_view_model.py`
	- `ocr_labeler/viewmodels/project/page_state_view_model.py`
	- `ocr_labeler/viewmodels/project/word_match_view_model.py`
- View layer:
	- `ocr_labeler/views/main_view.py`
	- `ocr_labeler/views/header/header.py`
	- `ocr_labeler/views/projects/project_view.py`
	- `ocr_labeler/views/projects/project_controls.py`
	- `ocr_labeler/views/projects/pages/{content,image_tabs,page_controls,text_tabs,word_match}.py`
	- `ocr_labeler/views/shared/{base_view,container_view}.py`
- Operations and services:
	- `ocr_labeler/operations/ocr/{navigation_operations,page_operations,text_operations,line_operations,ocr_service}.py`
	- `ocr_labeler/operations/persistence/{project_discovery_operations,project_operations,state_persistence_operations}.py`
	- `ocr_labeler/services/*`

Use this map as the first checkpoint when reconciling architecture docs with implementation.

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

## Threading Notes

- [Threading Architecture](threading-architecture.md)

## Doc Sync Tasks

- [Architecture Doc Sync Tasks](doc-sync-tasks.md)
