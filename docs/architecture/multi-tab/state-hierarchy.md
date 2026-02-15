# Multi-Tab State Hierarchy

Status: validated against `ocr_labeler/state/app_state.py` on 2026-02-15.

## Structure

```text
AppState (per tab)
├── available_projects: dict[str, Path]
├── selected_project_key: str | None
├── projects: dict[str, ProjectState]
│   ├── project_key_1: ProjectState
│   │   ├── page_states: dict[int, PageState]
│   │   │   ├── 0: PageState
│   │   │   ├── 1: PageState
│   │   │   └── ...
│   │   └── project: Project
│   └── project_key_2: ProjectState
├── current_project_key: str | None
└── _default_project_state: ProjectState  # lazy compatibility fallback
```

## Notes

- `projects` stores one `ProjectState` per loaded project.
- `selected_project_key` is UI-facing selection; `current_project_key` tracks the active loaded project.
- `project_state` returns the current entry from `projects`, or lazily creates `_default_project_state` when no project is active.
- `_default_project_state` exists for compatibility access paths and is not shared across tabs.

## Known Historical Issue

### Symptom

First navigation after loading projects in multiple tabs could disconnect one session.

### Root Cause (Historical)

`PageOperations.build_initial_page_parser()` created closures that instantiated new DocTR predictors per OCR call, causing resource contention under concurrent tab usage.

### Fix (Historical)

Refactor to lazy instance-level predictor reuse (`_get_or_create_predictor()`) in `ocr_labeler/operations/ocr/page_operations.py`.
