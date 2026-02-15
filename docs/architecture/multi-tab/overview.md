# Multi-Tab Architecture Overview

This document describes the per-session isolation model used for multi-tab behavior.

Status: validated against `ocr_labeler/app.py` on 2026-02-15.

## Core Principle

Create state, viewmodels, and views per route invocation (via `_create_session(...)`), not in `NiceGuiLabeler.__init__`.

Each tab receives isolated instances of:

- `AppState`
- `ProjectState`
- `PageState`
- `MainViewModel`
- `LabelerView`

## Pattern Summary

```python
class NiceGuiLabeler:
    def __init__(self, ...):
        # Keep config only
        self.project_root = project_root
        self.projects_root = projects_root

    def _create_session(self, ...):
        state = AppState(base_projects_root=self.projects_root)
        viewmodel = MainViewModel(state)
        view = LabelerView(viewmodel)
        view.build()

    def create_routes(self):
        @ui.page("/")
        def index():
            self._create_session(...)

        @ui.page("/project/{project_id}")
        def project_index(project_id: str):
            self._create_session(project_id=project_id, ...)

        @ui.page("/project/{project_id}/page/{page_id}")
        def project_page_index(project_id: str, page_id: str):
            self._create_session(project_id=project_id, page_id=page_id, ...)
```

## Why It Works

Each route invocation creates new objects for that session, so mutable state is not shared across tabs by default.

## Lifecycle Note

Session cleanup is registered with `ui.on("disconnect", ...)` to stop timers and clear listeners, reducing late callbacks after client teardown.
