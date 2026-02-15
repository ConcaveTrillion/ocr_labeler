# MVVM Refactor: Phases

Status: phased migration plan.

## Phase 1: Structure and File Movement

- Create consistent folder hierarchy for viewmodels/operations/services
- Move files to layer-appropriate locations
- Update imports across the codebase

## Phase 2: ViewModel Refactor

- Introduce shared base viewmodel patterns
- Normalize command and state exposure patterns
- Separate presentation concerns from state logic

## Phase 3: View Layer Refactor

- Standardize base view patterns
- Remove business logic from views
- Strengthen data binding consistency

## Phase 4: Operations and Services

- Remove UI coupling in operations
- Introduce service-level abstractions where useful
- Standardize error handling/logging paths

## Phase 5: State Management Cleanup

- Keep state classes focused on state + notifications
- Shift workflows to operations/services
- Harden persistence boundaries

## Phase 6: Testing and Validation

- Align tests with architecture layers
- Increase viewmodel/view unit coverage
- Maintain integration tests for workflow behavior
