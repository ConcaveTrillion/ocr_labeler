# Copilot Project Instructions: ocr-labeler

Concise, project-specific guidance for AI coding agents contributing to this repo.

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

## Code Generation
Always use context7 when I need code generation, setup or configuration steps, or
library/API documentation. This means you should automatically use the Context7 MCP
tools to resolve library id and get library docs without me having to explicitly ask.

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

## Testing & Coverage
- Test runner: `pytest` with coverage via `coverage` package (49 tests currently passing)
- Current structure: Tests in `tests/` with parallel structure to source
- Key test files:
  - `tests/test_app_state.py` - application state management (10 tests)
  - `tests/test_ground_truth.py` - ground truth loading and matching (21 tests)
  - `tests/test_project_state.py` - project navigation and loading (3 tests)
  - `tests/test_ui_refactoring.py` - UI component integration (3 tests)
  - `tests/models/test_project.py` - project model tests (12 tests)
- Coverage configured in `pyproject.toml`, HTML reports in `htmlcov/`
- Run tests: `uv run pytest`
- Coverage report: `uv run pytest --cov=ocr_labeler --cov-report=html`
- Coverage currently disabled in default pytest config for simplicity

## Dependency & Tooling Workflow
- **Dependency manager**: `uv` (see README). Use `uv add <pkg>` for new deps; ensure version constraints remain compatible with Python >=3.13.
- **Build**: `uv build` (hatchling backend)
- **Package management**: Local editable dependency on `pd-book-tools` via relative path (`../pd-book-tools`)
- **Quality tools**:
  - `pytest>=8.4.1` (testing)
  - `coverage` (test coverage, configured in pyproject.toml)
  - `debugpy>=1.8.5` (development debugging)
  - Note: `ruff`, `pre-commit`, `pylint`, `isort` not currently configured but can be added
- **Development**:
  - Run: `uv run ocr-labeler-ui <project-dir>`
  - Test: `uv run pytest`
  - Install deps: `uv sync`
- **GPU support**: Optional `opencv-python` for better image encoding performance; graceful fallback without it

## Current Implementation Status & Roadmap
- **Completed**: Basic navigation, OCR overlay display, ground truth comparison, lazy page loading, word-level matching UI with color coding (`WordMatchView`, `WordMatchViewModel`)
- **In Progress**: Word editing capabilities, bbox operations, save/load persistence (see TODOs.md Phase 1-2)
- **Next Phase**: Training/validation export, multi-page support, advanced word editing UI (see TODOs.md for detailed 46-task roadmap)
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

## Development Guidelines
- **Testing**: Add tests in parallel structure (`tests/<module>/test_<class>.py`); follow existing patterns
- **UI Components**: Use NiceGUI reactive patterns; avoid direct DOM manipulation
- **State Updates**: Always call `state.notify()` after state changes to trigger UI refresh
- **Async Operations**: Use proper async/await for OCR and navigation to prevent blocking
- **Error Resilience**: Handle missing dependencies gracefully (opencv, pd-book-tools features)
- **Performance**: Use lazy loading, image caching, and debounced updates where appropriate
- **Terminal Commands**: When using `run_in_terminal` tool, ALWAYS either:
  - Use `uv run <command>` for Python commands (preferred)
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
- **NiceGUI Version**: `>=2.22.2` for current feature set
- **Python Version**: `>=3.13` (configured in pyproject.toml)
- **Optional Dependencies**: `opencv-python` improves performance but not required

## What NOT to Do
- Don't block the UI thread with synchronous OCR operations
- Don't modify state without calling `notify()` for UI updates
- Don't create tight coupling between view components (use state as mediator)
- Don't ignore loading states (users need feedback during async operations)

## Adding New Test Cases
- Add tests in similar folder structure (`tests/<submodule>/test_<class>.py`)
- Follow existing naming patterns and test structures
- Mock external dependencies (`pd-book-tools`, file system) appropriately
- Test both success and failure paths for robustness

---
For detailed feature roadmap and implementation tasks, see `TODOs.md`. Current focus is on word-level editing capabilities and persistence features.
