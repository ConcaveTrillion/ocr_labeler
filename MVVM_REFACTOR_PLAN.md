# MVVM Architecture Refactor Plan

## Overview

This document outlines a comprehensive refactor to improve the separation of concerns between Model, ViewModel, and View components in the ocr-labeler project. The current architecture has some mixing of responsibilities, particularly with view models being scattered across different directories.

## Current Architecture Issues

### Problems Identified

1. **Mixed Responsibilities in `models/` Directory**
   - Data models (`Project`) coexist with view models (`WordMatchViewModel`, `AppStateViewModel`)
   - Binding models for UI frameworks are mixed with pure data structures
   - No clear separation between data transformation and UI binding logic

2. **Inconsistent ViewModel Organization**
   - Some view models are in `models/` (e.g., `WordMatchViewModel`)
   - Others are referenced but may be in different locations
   - No consistent naming or organization pattern

3. **State vs. Operations Confusion**
   - State management classes handle both state and operations
   - Operations are separated into `state/operations/` but could be better organized
   - Business logic is mixed with state persistence

4. **View Layer Coupling**
   - Views directly access state objects
   - No clear abstraction between UI and business logic
   - UI components contain navigation and business logic

## Proposed Architecture

### MVVM Pattern Implementation

```
ocr_labeler/
├── models/           # Pure data models and business entities
│   ├── __init__.py
│   ├── project.py
│   ├── word_match.py
│   ├── line_match.py
│   └── ...
├── viewmodels/       # Presentation logic and data transformation
│   ├── __init__.py
│   ├── app/
│   │   ├── app_state_viewmodel.py
│   │   └── project_list_viewmodel.py
│   ├── project/
│   │   ├── project_state_viewmodel.py
│   │   ├── page_navigation_viewmodel.py
│   │   └── word_match_viewmodel.py
│   └── shared/
│       └── base_viewmodel.py
├── views/            # UI components (NiceGUI)
│   ├── __init__.py
│   ├── app/
│   │   ├── main_view.py
│   │   └── header/
│   ├── project/
│   │   ├── project_view.py
│   │   ├── pages/
│   │   └── controls/
│   └── shared/
├── state/            # Application state management
│   ├── __init__.py
│   ├── app_state.py
│   ├── project_state.py
│   └── page_state.py
├── operations/       # Business operations and services
│   ├── __init__.py
│   ├── ocr/
│   │   ├── page_operations.py
│   │   └── ocr_service.py
│   ├── persistence/
│   │   ├── save_load_operations.py
│   │   └── export_operations.py
│   └── validation/
└── services/         # Cross-cutting concerns
    ├── __init__.py
    ├── notification_service.py
    └── configuration_service.py
```

### Component Responsibilities

#### Models (`models/`)
- **Purpose**: Pure data structures and business entities
- **Characteristics**:
  - No UI framework dependencies
  - No presentation logic
  - Serializable data structures
  - Business rules validation
- **Examples**:
  - `Project`: Project metadata and file management
  - `WordMatch`: OCR vs ground truth matching data
  - `LineMatch`: Line-level text comparison data

#### ViewModels (`viewmodels/`)
- **Purpose**: Presentation logic and data transformation for views
- **Characteristics**:
  - Transform model data for UI consumption
  - Handle UI state and commands
  - No direct UI component creation
  - Observable properties for data binding
- **Examples**:
  - `AppStateViewModel`: Application-level UI state
  - `ProjectStateViewModel`: Project-specific UI state
  - `WordMatchViewModel`: Word matching display logic

#### Views (`views/`)
- **Purpose**: UI components and layout using NiceGUI
- **Characteristics**:
  - Pure UI component composition
  - Data binding to view models
  - Event handling delegation to view models
  - No business logic
- **Examples**:
  - `MainView`: Main application layout
  - `ProjectView`: Project-specific UI
  - `WordMatchView`: Word matching display component

#### State (`state/`)
- **Purpose**: Application state management
- **Characteristics**:
  - Centralized state storage
  - State persistence and restoration
  - State change notifications
  - No business operations
- **Examples**:
  - `AppState`: Global application state
  - `ProjectState`: Project-specific state
  - `PageState`: Current page state

#### Operations (`operations/`)
- **Purpose**: Business operations and services
- **Characteristics**:
  - Pure business logic
  - No state management
  - No UI dependencies
  - Testable in isolation
- **Examples**:
  - `PageOperations`: OCR processing and page management
  - `SaveLoadOperations`: Persistence operations
  - `ExportOperations`: Data export functionality

## Refactor Phases

### Phase 1: Directory Structure & File Movement

#### 1.1 Create New Directory Structure
```bash
# Create new directories
mkdir -p ocr_labeler/viewmodels/{app,project,shared}
mkdir -p ocr_labeler/operations/{ocr,persistence,validation}
mkdir -p ocr_labeler/services
mkdir -p ocr_labeler/views/{app,project,shared}
```

#### 1.2 Move Existing Files

**From `models/` to `viewmodels/`:**
- `word_match_viewmodel.py` → `viewmodels/project/word_match_viewmodel.py`
- `app_state_viewmodel.py` → `viewmodels/app/app_state_viewmodel.py`
- `project_state_viewmodel.py` → `viewmodels/project/project_state_viewmodel.py`

**From `state/operations/` to `operations/`:**
- `page_operations.py` → `operations/ocr/page_operations.py`
- `line_operations.py` → `operations/ocr/line_operations.py`
- `project_operations.py` → `operations/persistence/project_operations.py`

**Keep in `models/`:**
- `project.py` (pure data model)
- `word_match_model.py` (data structure)
- `line_match_model.py` (data structure)

#### 1.3 Update Import Statements
Update all import statements throughout the codebase to reflect new locations.

### Phase 2: ViewModel Refactoring

#### 2.1 Create Base ViewModel Class
```python
# viewmodels/shared/base_viewmodel.py
from abc import ABC
from typing import Any, Callable, List
from nicegui import binding

@binding.bindable_dataclass
class BaseViewModel(ABC):
    """Base class for all view models providing common functionality."""

    _property_changed_callbacks: List[Callable[[str, Any], None]] = field(default_factory=list)

    def add_property_changed_listener(self, callback: Callable[[str, Any], None]):
        """Add a listener for property changes."""
        self._property_changed_callbacks.append(callback)

    def remove_property_changed_listener(self, callback: Callable[[str, Any], None]):
        """Remove a property change listener."""
        self._property_changed_callbacks.remove(callback)

    def notify_property_changed(self, property_name: str, value: Any):
        """Notify listeners of property changes."""
        for callback in self._property_changed_callbacks:
            callback(property_name, value)
```

#### 2.2 Refactor AppStateViewModel
- Extend `BaseViewModel`
- Separate UI binding logic from business logic
- Add command methods for UI actions

#### 2.3 Refactor ProjectStateViewModel
- Extend `BaseViewModel`
- Focus on project-specific presentation logic
- Separate navigation commands from state management

#### 2.4 Refactor WordMatchViewModel
- Extend `BaseViewModel`
- Clean separation of matching logic from display logic
- Add filtering and sorting commands

### Phase 3: View Layer Refactoring

#### 3.1 Create View Base Classes
```python
# views/shared/base_view.py
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from ..viewmodels.shared.base_viewmodel import BaseViewModel

TViewModel = TypeVar('TViewModel', bound=BaseViewModel)

class BaseView(ABC):
    """Base class for all views providing common functionality."""

    def __init__(self, viewmodel: TViewModel):
        self.viewmodel = viewmodel
        self._root = None

    @abstractmethod
    def build(self) -> Any:
        """Build and return the UI component."""
        pass

    @abstractmethod
    def refresh(self):
        """Refresh the view based on viewmodel changes."""
        pass
```

#### 3.2 Refactor Main View Components
- Make views extend `BaseView`
- Remove business logic from views
- Use data binding to view models
- Delegate commands to view model methods

#### 3.3 Implement Proper Data Binding
- Use NiceGUI binding system consistently
- Bind view properties to view model properties
- Handle view model change notifications

### Phase 4: Operations & Services Refactoring

#### 4.1 Create Service Layer
```python
# services/notification_service.py
class NotificationService:
    """Centralized notification service for user feedback."""

    def success(self, message: str):
        """Show success notification."""
        from nicegui import ui
        ui.notify(message, type="positive")

    def error(self, message: str):
        """Show error notification."""
        from nicegui import ui
        ui.notify(message, type="negative")

    def warning(self, message: str):
        """Show warning notification."""
        from nicegui import ui
        ui.notify(message, type="warning")

    def info(self, message: str):
        """Show info notification."""
        from nicegui import ui
        ui.notify(message)
```

#### 4.2 Refactor Operations Classes
- Remove UI dependencies from operations
- Use dependency injection for services
- Make operations stateless where possible
- Add proper error handling and logging

#### 4.3 Create OCR Service
```python
# operations/ocr/ocr_service.py
class OCRService:
    """Service for OCR operations."""

    def __init__(self, page_operations: PageOperations):
        self.page_operations = page_operations

    async def process_page(self, image_path: Path) -> Page:
        """Process a page with OCR."""
        return await self.page_operations.ensure_page(...)
```

### Phase 5: State Management Cleanup

#### 5.1 Simplify State Classes
- Remove business logic from state classes
- Focus on state storage and notifications
- Use operations classes for complex logic

#### 5.2 Implement State Persistence
- Create dedicated persistence operations
- Separate state serialization from state management
- Add state validation and migration

### Phase 6: Testing & Validation

#### 6.1 Update Test Structure
```
tests/
├── models/
├── viewmodels/
├── views/
├── state/
├── operations/
└── integration/
```

#### 6.2 Add ViewModel Tests
- Test presentation logic in isolation
- Mock model and service dependencies
- Test data transformation and commands

#### 6.3 Add View Tests
- Test UI component creation
- Test data binding
- Mock view models for UI testing

## Implementation Guidelines

### Coding Standards

#### ViewModel Guidelines
- View models should not import UI frameworks directly
- Use dependency injection for services
- Implement command pattern for UI actions
- Keep presentation logic separate from business logic

#### View Guidelines
- Views should only contain UI composition logic
- No business logic in views
- Use data binding for reactive updates
- Delegate all actions to view models

#### Model Guidelines
- Models should be pure data structures
- No dependencies on UI or external services
- Implement validation in models
- Keep serialization/deserialization logic in models

### Dependency Injection

#### Service Locator Pattern
```python
# services/service_locator.py
class ServiceLocator:
    """Service locator for dependency injection."""

    _services = {}

    @classmethod
    def register(cls, service_type: type, service_instance):
        cls._services[service_type] = service_instance

    @classmethod
    def get(cls, service_type: type):
        return cls._services.get(service_type)
```

#### Usage in ViewModels
```python
class WordMatchViewModel(BaseViewModel):
    def __init__(self, notification_service: NotificationService = None):
        self.notification_service = notification_service or ServiceLocator.get(NotificationService)
```

### Error Handling

#### Centralized Error Handling
```python
# services/error_handler.py
class ErrorHandler:
    """Centralized error handling service."""

    def handle_error(self, error: Exception, context: str = ""):
        """Handle and log errors appropriately."""
        logger.exception(f"Error in {context}: {error}")
        self.notification_service.error(f"An error occurred: {str(error)}")
```

### Performance Considerations

#### Lazy Loading
- Implement lazy loading in view models
- Cache expensive operations
- Use async operations for UI responsiveness

#### Memory Management
- Clean up event listeners
- Dispose of resources properly
- Implement weak references where appropriate

## Migration Strategy

### Incremental Migration
1. Start with leaf components (operations, services)
2. Migrate view models next
3. Update views to use new view models
4. Clean up state management
5. Update tests throughout

### Backward Compatibility
- Maintain API compatibility during migration
- Use feature flags for new functionality
- Gradual rollout with testing at each step

### Risk Mitigation
- Comprehensive test coverage before migration
- Feature flags for rollback capability
- Incremental commits with working functionality
- Code review at each major step

## Success Metrics

### Code Quality Metrics
- **Cyclomatic Complexity**: Reduce average complexity in views and view models
- **Test Coverage**: Maintain >90% coverage throughout refactor
- **Import Coupling**: Reduce cross-layer imports
- **Maintainability Index**: Improve overall maintainability score

### Architecture Metrics
- **Separation of Concerns**: Clear boundaries between layers
- **Dependency Direction**: Dependencies flow from view → viewmodel → model
- **Testability**: Each layer testable in isolation
- **Reusability**: Components reusable across different contexts

### Development Velocity Metrics
- **Build Time**: No significant increase in build times
- **Test Execution Time**: Maintain fast test feedback
- **Developer Productivity**: Easier to add new features
- **Bug Rate**: Reduced regression bugs

## Conclusion

This refactor will establish a solid MVVM architecture foundation for the ocr-labeler project, improving maintainability, testability, and developer productivity. The phased approach ensures minimal disruption while providing clear migration steps and success criteria.</content>
<parameter name="filePath">/home/linuxuser/ocr/ocr_labeler/MVVM_REFACTOR_PLAN.md
