# MVVM Refactor: Implementation Guidelines

Status: implementation guidance for planned refactor work.

## ViewModel Guidelines

- Avoid direct UI framework usage where practical
- Expose bindable state and command methods
- Keep presentation transformation logic centralized

## View Guidelines

- Keep views focused on layout/composition
- Delegate domain actions to viewmodels
- Prefer binding/callback patterns over embedded workflows

## Model Guidelines

- Keep models framework-agnostic
- Retain validation and serialization responsibilities in data layer

## Dependency Injection and Services

- Prefer explicit dependency injection for services
- Keep service boundaries clear (notifications, error handling, config)

## Performance and Reliability

- Preserve lazy-loading where it improves UX
- Ensure listeners/resources are cleaned up
- Keep heavy work off the UI event loop
