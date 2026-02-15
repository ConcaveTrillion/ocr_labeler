# Multi-Tab Pitfalls and Debugging

Status: operational checklist for debugging tab isolation issues.

Last validated: 2026-02-15.

## Avoid These Patterns

### 1) Shared state in app constructor

```python
class NiceGuiLabeler:
    def __init__(self):
        self.state = AppState()  # shared across tabs: avoid
```

### 2) Class-level mutable state

```python
class AppState:
    _shared_cache = {}  # shared across instances: avoid
```

### 3) Predictor/model creation inside transient closures

Prefer lazy instance-level caching of expensive OCR predictors instead of repeated per-call creation.

### 4) Mutating `_default_project_state` during app setup

Avoid initializing active project behavior by directly mutating fallback state. Let `load_project(...)` create/manage concrete `ProjectState` instances.

## Debugging Checklist

- Verify object isolation with `id(obj)` and `is not` checks.
- Modify one tab/session state and confirm other tabs do not change.
- Log instance IDs for `AppState`, `ProjectState`, and viewmodels.

## Shared-State Symptoms

- Navigation in one tab changes another tab.
- Loading/unloading projects in one tab impacts another tab.
- Cross-tab spinner/status coupling.

## Related Tests

See `tests/integration/test_multi_tab_isolation.py` for isolation-oriented tests.
