# Copilot Project Instructions: ocr-labeler

Concise, project-specific guidance for AI coding agents contributing to this repo.

## Dependency & Tooling Workflow

- Makefile-based VS code tasks for all common operations (build, test, lint, format, install, etc.)
- **Dependency manager**: `uv` (see README). Use `uv add <pkg>` for new deps; ensure version constraints remain compatible with Python >=3.13.
- **Build**: `uv build` VIA `Make: Build` task (hatchling backend)
- **Package management**: There is a local but non-editable dependency on `pd-book-tools` via relative path (`../pd-book-tools`)
- **Quality tools**:
  - `pytest>=8.4.1` (testing)
  - `coverage` (test coverage, configured in pyproject.toml)
  - `debugpy>=1.8.5` (development debugging)
  - `ruff`, `pre-commit`

## Development

### Code Generation

Always use context7 for finding library details when I need code generation, setup or configuration steps, or
library/API documentation. This means you should automatically use the Context7 MCP
tools to resolve library id and get library docs without me having to explicitly ask.

**For NiceGUI specifically**:
- Use the comprehensive NiceGUI patterns documented in the "NiceGUI Framework Patterns & Best Practices" section below for common tasks
- Use Context7 to fetch detailed NiceGUI API docs when:
  - Working with components not covered in this guide
  - Needing detailed API signatures or parameter options
  - Looking for new features or updated APIs
  - Investigating advanced use cases

### Task Execution Priority
  - Check for existing tasks in `.vscode/tasks.json` first (use `run_task` tool)
  - ALWAYS prefer VS Code tasks over terminal commands when available
  - Available tasks include all Makefile targets (test, lint, format, build, install, etc.)
    - Run: `Make: Run` task
    - Test: `Make: Test` task or VS Code `runTests` tool
    - Install deps: `Make: Install` task
  - This avoids user "ALLOW" prompts and provides better integration
  - Only use `run_in_terminal` as fallback when no appropriate task exists

### Code Quality Validation

ALWAYS run the `Make: CI Pipeline` task after finishing any code changes**
This ensures proper formatting, linting, testing, and build validation before presenting code to the user

## Testing & Coverage
- Test runner: `Make: Test` task or VS Code `runTests` tool (uses `pytest` VIA with coverage via `coverage` package)
- Coverage configured in `pyproject.toml`, HTML reports in `htmlcov/`
- Coverage report: `uv run pytest --cov=ocr_labeler --cov-report=html`
- Coverage currently disabled in default pytest config for simplicity
- Add tests in parallel structure (`tests/<module>/<submodule>.../test_<class>.py`); follow existing patterns.
- **CRITICAL: NEVER use `run_in_terminal` tool to run pytest directly - ALWAYS use the `runTests` tool or `Make: Test` task instead**
  - this provides:
    - better integration
    - detailed test output
    - avoids user prompts.
  - Using terminal commands for AI testing violates project workflow requirements.




## Adding New Test Cases
- Add tests in similar folder structure (`tests/<submodule>/test_<class>.py`)
- Follow existing naming patterns and test structures
- Mock external dependencies (`pd-book-tools`, file system) appropriately
- Test both success and failure paths for robustness

## Core Domain & Architecture
- Purpose: NiceGUI-based web interface for processing public domain book scans. Performs OCR via `pd-book-tools`, displays overlays, and allows ground-truth comparison. Future: word-level editing and training data export.
- Tech Stack: NiceGUI (web UI), Python 3.13+, `uv` package manager
- Main components:
  - **Application Layer**: `ocr_labeler.app.NiceGuiLabeler` - main entry point
  - **State Management**:
    - `ocr_labeler.state.AppState` - application-wide state (project selection, UI settings)
    - `ocr_labeler.state.ProjectState` - project-specific state (navigation, lazy page loading)
    - `ocr_labeler.state.GroundTruth` - ground truth text management from `pages.json`
    - `ocr_labeler.state.PageLoader` - async OCR processing via `pd-book-tools`
  - **View Components**: Modular NiceGUI components in `ocr_labeler.views.*`:
    - `main_view.LabelerView` - main orchestrator with header + content composition
    - `header.HeaderBar` - project controls and navigation
    - `content.ContentArea` - main content splitter with image/text tabs
    - `image_tabs.ImageTabs` - overlay image variants display
    - `text_tabs.TextTabs` - OCR vs ground truth text comparison
    - `word_match.WordMatchView` - word-level matching with color coding and filtering
    - `page_controls.PageControls` - prev/next/goto navigation
    - `project_load_controls.ProjectLoadControls` - project directory selection
  - **Models**: Data structures and view models in `ocr_labeler.models.*`:
    - `project.Project` - project file management
    - `word_match.WordMatchViewModel` - OCR/GT matching logic and statistics
  - **CLI**: `ocr_labeler.cli.main()` entry point with argparse


## Key library use:
  - `pd_book_tools`
    - `pd_book_tools/geometry/`: Primitive spatial types (`Point`, `BoundingBox`) with normalization semantics (normalized vs pixel). All downstream logic relies on correct `is_normalized` flags.
    - `pd_book_tools/ocr/`: OCR result object model (`Word`, `Block`, `Page`) plus matching (`ground_truth_matching.py`), external OCR/tool adapters (`cv2_tesseract.py`, `doctr_support.py`), and utilities.
    - `pd_book_tools/image_processing/`: CV + (optional) GPU variants (cupy / opencv-cuda) for transformations (color, crop, morph, threshold, etc.). Many files are thin wrappers—keep them small & focused.
    - Data flow (typical): raw OCR tool output -> `Word`s (normalized or pixel bboxes) -> grouped into `Block`s (hierarchy Lines / Paragraphs / Blocks) -> aggregated into `Page` -> refined (bbox refine/crop) -> ground truth match augmentation.
    - Coordinate systems: normalized ([0,1]) vs pixel (image dimensions). Critical to track & enforce consistency. See next section.
      - `BoundingBox` & `Point` track `is_normalized` (True => values in [0,1]; False => pixel space). Inference happens on construction if unspecified.
      - Cross-box operations (union, intersection, IoU, merge/split in `Word`) REQUIRE matching coordinate systems; code raises `ValueError` when mismatched.
      - Scaling APIs:
        - `BoundingBox.scale(width, height)`: ONLY for normalized -> pixel.
        - `BoundingBox.normalize(width, height)`: ONLY for pixel -> normalized.
        - `Word.scale(width, height)`: deep-copies; if already pixel-space returns unchanged deep copy (logs info); if normalized, scales bbox to pixel, leaves ground-truth bbox untouched.
    - Object Model Highlights
      - `Word`:
        - Deep copy pattern relies on `to_dict` / `from_dict` for safety (lists/dicts cloned). Follow this when creating variant instances.
        - `merge` & `split` add provenance flags (`ground_truth_match_keys['split']`). Preserve existing flags when extending.
        - On merges: label dedup happens via set + order-stable dict trick; replicate pattern if extending label logic.
      - `Block`:
        - Hierarchical: contains either `Word`s or child `Block`s (see `child_type`). Sorting is positional (top-left y then x); advanced multi-column sorting is TODO—don’t over-engineer new ordering heuristics without tests.
        - Bounding box auto-computed via `BoundingBox.union` if not provided.
      - `Page`:
        - Similar aggregation pattern; recompute page bbox after structural edits.
        - Rendering/debug functions (drawing bboxes) rely on consistent pixel coordinates—ensure you normalize or scale before drawing.

### GPU support

`opencv-python` for better image encoding performance; graceful fallback without it (generally)


## Current Implementation Status & Roadmap
- **Completed**: Basic navigation, OCR overlay display, ground truth comparison, lazy page loading, word-level matching UI with color coding (`WordMatchView`, `WordMatchViewModel`)
- **In Progress**: Word editing capabilities, bbox operations, save/load persistence (see `docs/planning/roadmap/phase-3-editing-core.md`)
- **Next Phase**: Training/validation export, multi-page support, advanced word editing UI (see `docs/planning/README.md`)
- **Architecture Status**: Fully modular component architecture complete with clean imports using the new modular structure

## Key Architectural Patterns
- **State Management**: Clear separation between app-wide (`AppState`) and project-specific (`ProjectState`) concerns
- **Async Loading**: Lazy OCR processing with loading states to prevent UI blocking
- **Component Composition**: NiceGUI components built via composition pattern with `build()` methods
- **Reactive Updates**: State change notifications trigger UI refresh cycles
- **Error Handling**: Graceful degradation with user notifications via `ui.notify()`

## Data Flow & Integration
- **Project Loading**: Directory scan → image discovery → lazy OCR via `pd-book-tools`
- **Ground Truth**: Optional `pages.json` file provides GT text mapping (case-insensitive filename matching)
- **Page Navigation**: Index-based with bounds checking, async background OCR loading
- **Image Overlays**: Generated via `pd-book-tools` CV functions with fallback caching
- **Word Matching**: OCR vs GT alignment using fuzzy string matching with configurable thresholds


## NiceGUI Framework Patterns & Best Practices

This project uses NiceGUI `>=2.22.2` for the web UI. Understanding these patterns is critical for maintaining consistency and avoiding common pitfalls.

### Core Concepts

- **Component-Based Architecture**: UI is built from composable components (views) that inherit from `BaseView[TViewModel]`
- **Reactive Binding System**: ViewModels expose bindable properties that automatically update the UI when changed
- **Event Loop Integration**: NiceGUI manages an asyncio event loop per session; use NiceGUI-provided async APIs, not raw asyncio
- **Per-Session State Isolation**: Each browser tab gets its own state instances via the `@ui.page("/")` decorator

### Essential Components Reference

#### Layout Components
```python
ui.column()          # Vertical layout container
ui.row()             # Horizontal layout container
ui.splitter()        # Resizable split pane (value=50 is 50% split)
ui.scroll_area()     # Scrollable content area
```

Common usage:
```python
with ui.column().classes("w-full h-full flex flex-col") as container:
    # Nested components here
    pass
```

#### Data Display Components
```python
ui.tabs()            # Tab headers (use with ui.tab and ui.tab_panels)
ui.tab()             # Individual tab header
ui.tab_panels()      # Tab content container
ui.image()           # Image display (supports data URLs, paths)
ui.label()           # Text display
ui.button()          # Action button with on_click handler
ui.codemirror()      # Code/text editor with syntax highlighting
ui.card()            # Material card container
ui.icon()            # Material Design icons
```

#### Input Components
```python
ui.number()          # Numeric input
ui.select()          # Dropdown selection
ui.input()           # Text input
```

#### Feedback Components
```python
ui.spinner()         # Loading spinner (size="sm|md|lg|xl", color="primary|...")
ui.notify()          # Toast notification (type="positive|negative|warning|info")
```

Example:
```python
ui.notify("Operation successful", type="positive")
with ui.column().classes("items-center"):
    ui.spinner(size="xl", color="primary")
```

#### Styling
```python
.classes("...")      # Add Tailwind CSS classes
.props("...")        # Add Quasar/HTML props (e.g., "dense no-caps")
.mark("...")         # Add marker for JavaScript integration
```

### Reactive Binding Patterns (Critical)

**ViewModels MUST use `@binding.bindable_dataclass` decorator:**
```python
from nicegui import binding
from dataclasses import dataclass, field

@binding.bindable_dataclass
class PageStateViewModel(BaseViewModel):
    current_page: int = 0
    is_loading: bool = False
    status_message: str = ""
```

#### One-Way Binding (ViewModel → UI)
Use when UI should reflect ViewModel state but not update it:
```python
binding.bind_from(
    target_object=self.prev_button,  # UI element
    target_name="disabled",           # UI property
    source_object=self.viewmodel,     # ViewModel
    source_name="prev_disabled"       # ViewModel property
)

# Shorthand for visibility:
self.spinner.bind_visibility_from(
    target_object=self.viewmodel,
    target_name="is_loading"
)

# Shorthand for text:
self.label.bind_text_from(
    target_object=self.viewmodel,
    target_name="status_message"
)
```

#### Two-Way Binding
Use for form inputs that should update ViewModel state:
```python
binding.bind(
    target_object=self.select,
    target_name="value",
    source_object=self.app_state_model,
    source_name="selected_project_key"
)
```

#### When NOT to Use Binding
**Image sources require callback-based updates**, not binding. Binding to `ui.image().source` can cause UI glitches:
```python
# WRONG - don't bind image sources:
# binding.bind_from(self.image, "source", self.viewmodel, "image_url")

# CORRECT - use callbacks:
def update_image(self):
    image_url = self.viewmodel.get_image_url()
    self.image.set_source(image_url)

self.viewmodel.add_property_changed_listener(
    lambda prop, val: self.update_image() if prop == "current_page" else None
)
```

### Async/Threading Best Practices (Critical)

**ALWAYS use NiceGUI's async APIs**, not raw asyncio. Direct asyncio usage can cause websocket disconnections and UI freezes.

#### `run.io_bound()` - For Blocking I/O
Use for any blocking operation (file I/O, OCR processing, image encoding):
```python
from nicegui import run

# File operations
page_data = await run.io_bound(self.project_state.get_page, page_index)

# Image processing
encoded = await run.io_bound(self._encode_image_to_data_url, image_data)

# OCR operations
await run.io_bound(current_page.refresh_page_images)
```

#### `background_tasks.create()` - For Non-Blocking Async Tasks
Use for fire-and-forget async operations:
```python
from nicegui import background_tasks

# Background page loading
background_tasks.create(self._background_load())

# Async UI updates
background_tasks.create(self._update_image_sources_async())
```

#### Async Callbacks
NiceGUI automatically handles async callbacks - just use `async def`:
```python
async def _reload_with_ocr(self):
    ui.notify("Rerunning OCR...", type="info")
    success = await run.io_bound(self._perform_ocr)
    ui.notify("OCR complete!" if success else "OCR failed",
              type="positive" if success else "negative")

ui.button("Reload OCR", on_click=self._reload_with_ocr)
```

#### Context Managers for Async Operations
Manage UI state across async operations:
```python
@contextlib.asynccontextmanager
async def _action_context(self, message: str):
    self._overlay.set_visibility(True)
    self._status_label.set_text(message)
    try:
        yield
    finally:
        self._overlay.set_visibility(False)

# Usage:
async def save_page(self):
    async with self._action_context("Saving page..."):
        await run.io_bound(self.project_state.save_page)
```

#### What NOT to Do
**Never use these raw asyncio APIs** - they bypass NiceGUI's websocket management:
```python
# WRONG:
asyncio.create_task(some_coro())        # Use background_tasks.create() instead
loop.run_in_executor(None, blocking)    # Use run.io_bound() instead
asyncio.to_thread(blocking)             # Use run.io_bound() instead
```

See `/home/linuxuser/ocr/ocr_labeler/docs/architecture/async/migration-patterns.md` for detailed migration examples.

### Project-Specific Architectural Patterns

#### ViewModel/View Separation
```python
# Views inherit from BaseView[TViewModel]
class PageControls(BaseView[PageStateViewModel]):
    def __init__(self, viewmodel: PageStateViewModel):
        super().__init__(viewmodel)
        # UI elements created in build()

    def build(self) -> ui.column:
        with ui.column() as self._root:
            # Build UI here
            pass
        return self._root
```

#### Property Change Notification
For custom refresh logic beyond data binding:
```python
# In ViewModel:
def notify_property_changed(self, property_name: str, value: Any):
    for callback in self._property_changed_callbacks:
        callback(property_name, value)

# In View:
self.viewmodel.add_property_changed_listener(self._on_viewmodel_changed)

def _on_viewmodel_changed(self, prop: str, value: Any):
    if prop == "current_page":
        self._refresh_content()
```

#### Per-Session Isolation
Each browser tab gets isolated state via the page decorator:
```python
# In app.py
@ui.page("/")
def index():
    # Fresh instances per session
    state = AppState()
    viewmodel = MainViewModel(state)
    view = LabelerView(viewmodel)
    view.build()

    # Cleanup on tab close
    def on_disconnect():
        # Clean up session resources
        pass
    ui.on("disconnect", on_disconnect)
```

#### Component Composition
Parent views build child view components:
```python
class ProjectView(BaseView[ProjectStateViewModel]):
    def build(self) -> ui.column:
        with ui.column() as self._root:
            # Create child views
            self.page_controls = PageControls(self.viewmodel.page_viewmodel)
            self.page_controls.build()

            self.content = ContentArea(self.viewmodel)
            self.content.build()
        return self._root
```

### Common Gotchas & Solutions

| Issue | Solution |
|-------|----------|
| UI freezes during operations | Wrap blocking code in `run.io_bound()` |
| Websocket disconnects during background tasks | Use `background_tasks.create()` instead of `asyncio.create_task()` |
| Image not updating when bound | Use callback pattern, not binding for image sources |
| Component not showing up | Make sure to call `.build()` after creating the component instance |
| Nested components broken | Use context manager: `with ui.column(): ...` |
| State changes across tabs | Each tab has separate state - this is intentional per-session isolation |
| Memory leaks on disconnect | Implement `on_disconnect` cleanup for session resources |

### Documentation Resources

- **NiceGUI Version**: `>=2.22.2` (project requirement)
- **Official Docs**: https://nicegui.io
- **API Reference**: https://nicegui.io/documentation (fetch via Context7 for detailed lookups)
- **Project Async Migration**: `/home/linuxuser/ocr/ocr_labeler/docs/architecture/async/overview.md`



- **UI Components**: Use NiceGUI reactive patterns; avoid direct DOM manipulation
- **State Updates**: Always call `state.notify()` after state changes to trigger UI refresh
- **Async Operations**: Use proper async/await for OCR and navigation to prevent blocking
- **Error Resilience**: Handle missing dependencies gracefully (opencv, pd-book-tools features)
- **Performance**: Use lazy loading, image caching, and debounced updates where appropriate
- **Terminal Commands**: When using `run_in_terminal` tool, ALWAYS either:
  - Use `uv run <command>` for Python when you are forced to use run in terminal commands. If a vs code task exists, prefer that.
  - Prefix with `source .venv/bin/activate && <command>` for direct console scripts
  - Never run `ocr-labeler-ui` or other console entry points without proper environment activation

## Common Patterns to Follow
- **View Components**: Initialize with `__init__()`, build UI with `build()`, update with dedicated methods
- **State Binding**: Use NiceGUI's binding system for reactive data connections
- **Navigation**: Prepare spinners first, then delegate to async methods to prevent blocking
- **File Handling**: Use `Path` objects, handle missing files gracefully
- **Logging**: Use module-level loggers with appropriate levels (`debug`, `info`, `warning`, `error`)

## Integration Notes
- **pd-book-tools Dependency**: Core OCR functionality via relative path import; ensure both repos are siblings.
- **NiceGUI**: `>=2.22.2` for current feature set. See comprehensive patterns in "NiceGUI Framework Patterns & Best Practices" section.
- **Python Version**: `>=3.13` (configured in pyproject.toml)
- **Optional Dependencies**: `opencv-python` improves performance but not required

## What NOT to Do
- Don't block the UI thread with synchronous OCR operations
- Don't modify state without calling `notify()` for UI updates
- Don't create tight coupling between view components (use state as mediator)
- Don't ignore loading states (users need feedback during async operations)


---
For detailed feature roadmap and implementation tasks, see `docs/planning/README.md`. Current focus is on word-level editing capabilities and persistence features.
