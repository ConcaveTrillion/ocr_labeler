# MVVM Refactor: Target Architecture

Status: target-state planning reference.

## Proposed Layout

```text
ocr_labeler/
├── models/
├── viewmodels/
│   ├── app/
│   ├── project/
│   └── shared/
├── views/
│   ├── app/
│   ├── project/
│   └── shared/
├── state/
├── operations/
│   ├── ocr/
│   ├── persistence/
│   └── validation/
└── services/
```

## Layer Responsibilities

### Models

- Pure data structures and business entities
- No UI dependencies

### ViewModels

- Presentation logic and UI-facing commands
- No direct UI component construction

### Views

- NiceGUI UI composition and binding
- Delegate actions to viewmodels

### State

- State storage, lifecycle, and notifications
- Avoid embedding domain operations

### Operations/Services

- Business logic and cross-cutting services
- Testable independent of UI
