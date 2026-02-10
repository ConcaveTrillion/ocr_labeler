# Multi-Tab Architecture

## Overview

The OCR Labeler supports multiple browser tabs/sessions, with each tab maintaining completely isolated state. This document explains how the isolation is achieved and what to be aware of when developing.

## Architecture Pattern: Per-Session Instances

### Key Principle

**State, viewmodels, and views are created INSIDE the `@ui.page` handler, not in `NiceGuiLabeler.__init__`.**

This ensures that each browser tab that opens the page gets its own independent instances of:
- `AppState` - application-level state
- `ProjectState` - project-specific state (one per loaded project)
- `PageState` - page-specific state (one per page in a project)
- `MainViewModel` - main view model orchestrating UI
- `LabelerView` - main view component

### Implementation Details

#### app.py Structure

```python
class NiceGuiLabeler:
    def __init__(self, project_root, projects_root, ...):
        # Store ONLY configuration parameters
        self.project_root = project_root
        self.projects_root = projects_root
        # ... other config ...

        # Prepare shared resources (font CSS)
        self.font_css = self._prepare_font_css()

        # DO NOT create state/viewmodel/view here!

    def create_routes(self):
        @ui.page("/")
        def index():
            # Create fresh instances for THIS session/tab
            state = AppState(
                base_projects_root=self.projects_root,
                # ...
            )
            viewmodel = MainViewModel(state)
            view = LabelerView(viewmodel)
            view.build()
```

#### Why This Works

When a user opens multiple tabs:
1. Tab 1 loads → `index()` called → creates `state1`, `viewmodel1`, `view1`
2. Tab 2 loads → `index()` called → creates `state2`, `viewmodel2`, `view2`

Each set of instances is completely independent. Changes in one tab don't affect the other.

## Common Pitfalls (AVOID)

### ❌ DON'T: Create Shared State

```python
# BAD - creates shared state
class NiceGuiLabeler:
    def __init__(self):
        self.state = AppState()  # WRONG! Shared across tabs!
```

### ❌ DON'T: Use Class Variables for State

```python
# BAD - class variables are shared
class AppState:
    _shared_cache = {}  # WRONG! All instances share this!
```

### ❌ DON'T: Create Predictors/Models in Closures

```python
# BAD - creates new predictor every call, causing resource conflicts
def build_parser():
    def _get_predictor():
        return get_default_doctr_predictor()  # WRONG! New instance every time

    def _parse(img):
        predictor = _get_predictor()  # Creates new model
        return predictor(img)
    return _parse

# GOOD - reuse predictor at instance level
class Operations:
    def __init__(self):
        self._predictor = None

    def _get_or_create_predictor(self):
        if self._predictor is None:
            self._predictor = get_default_doctr_predictor()
        return self._predictor
```

### ❌ DON'T: Set Default ProjectState in App Init

```python
# BAD - triggers lazy initialization of _default_project_state
state = AppState(...)
state.project_state.project_root = Path(...)  # WRONG!
```

The `project_state` property lazily creates `_default_project_state`. This is only used as a fallback before any project is loaded. Setting properties on it in app initialization can cause confusion because when a project IS loaded, it creates a different `ProjectState` in the `projects` dict.

### ✅ DO: Let Project Loading Set Project Root

```python
# GOOD - project root is set when project is loaded
await state.load_project(project_path)  # Sets up proper ProjectState
```

## State Hierarchy

```
AppState (per tab)
├── projects: dict[str, ProjectState]  # One per loaded project
│   ├── project_key_1: ProjectState
│   │   ├── page_states: dict[int, PageState]  # One per page
│   │   │   ├── 0: PageState
│   │   │   ├── 1: PageState
│   │   │   └── ...
│   │   └── project: Project
│   └── project_key_2: ProjectState
│       └── ...
└── _default_project_state: ProjectState  # Fallback only, rarely used
```

### Important Notes

- **`projects` dict**: Stores one `ProjectState` per loaded project, keyed by project name
- **`current_project_key`**: Points to the currently active project in `projects`
- **`_default_project_state`**: Created lazily as a fallback when `project_state` property is accessed before any project is loaded. This is intentionally ephemeral and gets replaced once a real project loads.

## Fixed Issues

### Issue: Disconnection on First Navigation After Loading Projects in Multiple Tabs

**Symptom:** Loading different projects in different tabs and clicking "next" for the first time caused a disconnection error in one tab.

**Root Cause:** The `PageOperations.build_initial_page_parser()` method created a closure that instantiated a NEW DocTR predictor every time OCR was needed. When multiple tabs navigated simultaneously and triggered OCR, they competed to create and use DocTR predictors concurrently, causing resource conflicts and WebSocket disconnections.

**Solution:** Refactored `PageOperations` to store the predictor as an instance variable with lazy initialization via `_get_or_create_predictor()`. Now each `PageOperations` instance (one per `ProjectState`) gets and reuses its own predictor, avoiding concurrent creation conflicts.

**Files Changed:**
- [ocr_labeler/operations/ocr/page_operations.py](ocr_labeler/operations/ocr/page_operations.py): Added `_docTR_predictor` instance variable and `_get_or_create_predictor()` method

See `tests/integration/test_multi_tab_isolation.py` for comprehensive tests that verify:
- Multiple `AppState` instances are independent
- Loading projects in separate states maintains isolation
- The app creates isolated instances per route call
- `_default_project_state` is not shared

## Debugging Tips

### How to Verify Isolation

1. **Check object identity**: Use `id(object)` or `is` to verify different instances
   ```python
   assert state1 is not state2
   assert id(state1.projects) != id(state2.projects)
   ```

2. **Check state independence**: Modify one instance, verify the other is unchanged
   ```python
   state1.selected_project_key = "project1"
   state2.selected_project_key = "project2"
   assert state1.selected_project_key != state2.selected_project_key
   ```

3. **Log instance IDs**: Add debug logging to track which instance is active
   ```python
   logger.debug(f"AppState instance: {id(self)}")
   ```

### Common Symptoms of Shared State

- ✗ Navigating in one tab changes the page in another tab
- ✗ Loading a project in one tab "unloads" it in another tab
- ✗ UI updates in one tab affect another tab
- ✗ One tab's spinner appears/disappears based on other tab's actions

If you see these symptoms, check for:
1. State/viewmodel/view created in `__init__` instead of `@ui.page` handler
2. Class variables being used for instance state
3. Singleton patterns or module-level state
4. Improper use of `_default_project_state`

## Future Considerations

### Session Storage (Not Currently Used)

NiceGUI provides `app.storage.user` for per-session storage that persists across page reloads. We don't currently use this because:
1. State is created fresh on each page load (simpler)
2. We don't need persistence across page reloads
3. Simpler debugging and testing

If future requirements need session persistence, `app.storage.user` would be the appropriate mechanism.

### Cleanup on Tab Close

Currently, when a tab closes, Python's garbage collector cleans up the instances. If we need explicit cleanup (e.g., saving state, closing connections), we'd need to:
1. Use `ui.on_disconnect()` callbacks
2. Implement cleanup methods on state classes
3. Be careful not to break other open tabs

## Summary

The multi-tab architecture is simple but requires discipline:

**✅ DO:**
- Create state/viewmodel/view in `@ui.page` handler
- Use instance variables for state
- Let project loading manage ProjectState lifecycle
- Test for proper isolation

**❌ DON'T:**
- Create state in `__init__`
- Use class variables for state
- Manually set properties on `_default_project_state`
- Assume state is shared or persistent

Following these patterns ensures each tab operates independently, providing a better user experience and avoiding hard-to-debug state conflicts.
