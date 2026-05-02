OCR Labeler (NiceGUI UI)
========================

Minimal web UI for navigating OCR page images, viewing overlays, and
comparing OCR output with ground truth text. Built with
[NiceGUI](https://nicegui.io/) and a lightweight state layer that lazily
loads and OCRs pages via `pd-book-tools`.

Documentation
-------------

- Architecture docs: [docs/architecture/README.md](docs/architecture/README.md)
- Planning and roadmap docs: [docs/planning/README.md](docs/planning/README.md)
- Current editing roadmap focus: [docs/planning/roadmap/editing-core.md](docs/planning/roadmap/editing-core.md)

AI Doc Retrieval Checklist
--------------------------

Use this order to keep AI prompts small and rely on canonical docs:

1. Read project overview in this README.
2. Read architecture index: [docs/architecture/README.md](docs/architecture/README.md).
3. Read planning index: [docs/planning/README.md](docs/planning/README.md).
4. For NiceGUI behavior, read: [docs/architecture/nicegui-patterns.md](docs/architecture/nicegui-patterns.md).
5. For async behavior, read: [docs/architecture/async/overview.md](docs/architecture/async/overview.md) and [docs/architecture/async/migration-patterns.md](docs/architecture/async/migration-patterns.md).

Rules:

- Treat docs as source of truth; do not duplicate large guidance in agent instruction files.
- If implementation changes behavior, update the matching doc in `docs/`.
- Use Make targets as the default for install, lint, test, build, and run;
  use VS Code tasks as optional wrappers when in VS Code.

Current Capabilities
--------------------

- Open a project directory containing page images (`.png`, `.jpg`, `.jpeg`).
- Auto-lazy load & OCR each page the first time you navigate to it.
- Navigate pages (Prev / Next / direct page number input).
- Display multiple overlay variants (original, paragraphs, lines, words,
  mismatches -- where available from the underlying OCR lib).
- Show OCR text and (optional) ground truth text side by side.
- Auto-populate ground truth text from an optional `pages.json` file mapping
  image filename -> ground truth string. Raw PGDP text is preprocessed
  via `PGDPResults` at load time (diacritics, dashes, footnotes, quotes,
  proofer notes).
- Save current page edits to JSON and image files for persistence.
- Save Project: bulk-persist all worked pages in a single action.
- Word-level editing: merge, split, delete, rebox, and per-word GT inline
  editing with Tab/Shift-Tab keyboard navigation.
- Word tag editing: assign text style labels (italics, bold, small caps,
  blackletter, etc.), style scopes (whole/part), and word components
  (footnote markers, etc.) via toolbar controls and a word edit dialog.
- Word edit dialog with interactive zoom slider (0.5x--2.0x) for image
  inspection.
- Paragraph actions: merge, delete, split-after-line, split-by-selected-lines.
- Per-word validation state with line/paragraph rollup, UI toggle, and
  persistence across save/load and auto-cache.
- GT rematch + overlay/cache refresh after structural edits.
- Bbox refinement: rebox workflow, rebox auto-refine, selection refine
  actions for word/line/paragraph scopes.
- DocTR training/validation export dialog with scope selection (current
  page / all validated pages) and style-based filtering.
- Backend project export formats (json/jsonl/csv).
- Provenance tracking: user page envelope with app version, toolchain
  versions, OCR engine metadata, and image fingerprint.
- OS-aware persistence paths (XDG on Linux, Library on macOS, APPDATA on
  Windows).

Planned / Not Yet Implemented (see `docs/planning/README.md` for full roadmap)
------------------------------------------------------------------------------

- Merge multiple JSON project files with page index offsets
- Full persistence metadata schema with session restore
- Derived word/line cache optimization
- Performance polish (debounced GT edits, graceful fallbacks)

Quick Start
-----------

Prerequisites
-------------

- Python 3.13+ (project is configured with `requires-python = ">=3.13"`).
- [uv](https://github.com/astral-sh/uv) recommended for fast, locked installs (a `uv.lock` is included).
- Optional: `opencv-python` for image encoding and image-dependent display
  helpers. In many setups it is available transitively, but install it
  manually if overlays/previews are missing (see section below).

Clone Repository
----------------

This project depends on `pd-book-tools`, which is fetched automatically from
GitHub by uv (configured in `pyproject.toml`). No local clone of
`pd-book-tools` is required.

```bash
git clone https://github.com/ConcaveTrillion/pd-ocr-labeler.git
cd pd-ocr-labeler
```

Install Dependencies
--------------------

`pd-book-tools` is resolved automatically from GitHub by uv — no manual clone needed.

**CUDA is highly recommended.** OCR inference is significantly faster on GPU. Ensure the appropriate
PyTorch CUDA index is configured before syncing (see the
[pd-book-tools README](https://github.com/ConcaveTrillion/pd-book-tools#readme) for setup details).

Using the Makefile (recommended):

```bash
make install
```

This will install dependencies and set up pre-commit hooks for development.

Alternatively, using uv directly:

```bash
uv sync
```

Or ad‑hoc run without a full sync (will resolve on the fly):

```bash
uv run python -c "import nicegui"
```

Prepare a Project Directory
---------------------------

Create (or choose) a folder with page images you want to inspect, e.g.:

```text
sample_project/
 001.png
 002.png
 003.jpg
 pages.json          (optional ground truth mapping)
```

`pages.json` (optional) example:

```json
{
 "001.png": "Ground truth text for first page...",
 "002.png": "Second page ground truth..."
}
```

Keys are matched case‑insensitively; variants without extension (e.g. "001") also map if provided.

Run the UI (CLI)
----------------

A console entrypoint `pd-ocr-labeler-ui` is installed.

Preferred launch from repo root (uses current directory as project):

```bash
make run
```

Basic launch with an explicit project directory:

```bash
uv run pd-ocr-labeler-ui sample_project
```

Change host/port (e.g. access from another device on LAN):

```bash
uv run pd-ocr-labeler-ui sample_project --host 0.0.0.0 --port 9000
```

Start with project chooser behavior:

```bash
uv run pd-ocr-labeler-ui
```

Auto-load happens only when the resolved `project_dir` is a valid project
directory (contains supported page images).

Increase logging verbosity (repo root + current directory as project):

```bash
make run-verbose
```

For an explicit project directory:

```bash
uv run pd-ocr-labeler-ui sample_project -v        # DEBUG app logs
uv run pd-ocr-labeler-ui sample_project -vv       # DEBUG app + pd-book-tools
uv run pd-ocr-labeler-ui sample_project -vvv      # DEBUG app + dependencies
```

Enable isolated page timing logs in the CLI (repo root + current directory as project):

```bash
make run-page-timing
```

For an explicit project directory:

```bash
uv run pd-ocr-labeler-ui sample_project --page-timing
```

This prints only page timing events (`pd_ocr_labeler.page_timing`) such as
`page_load_timing`, `page_load_timing_step`, and `page_navigation_timing`.

Then open: <http://127.0.0.1:8080/> (or your chosen host/port)

Using the Interface
-------------------

1. Project Directory: Confirm (or edit) the path shown, then click Open.
2. Navigation: Use Prev / Next or type a page number
   (press Enter or defocus field).
3. Tabs (left): Switch between overlay variants;
   a single central spinner shows while a page is loading.
4. Tabs (right): View Ground Truth vs OCR text.
   Ground truth is blank if not found in `pages.json`.
5. Saving: Click "Save Page" to persist current page edits to JSON and image files in `local-data/labeled-ocr/`.

Custom Fonts (Optional)
-----------------------

`NiceGuiLabeler` accepts `monospace_font_name` and `monospace_font_path`.
If a font path is supplied (or the bundled `DPSansMono.ttf` is available),
the app injects font CSS at startup and applies it to
`.monospace`/CodeMirror elements.

Example usage:

```python
NiceGuiLabeler(project_root, monospace_font_name="MyMono", monospace_font_path=Path("fonts/MyMono.ttf"))
```

OpenCV Optional Dependency
--------------------------

OpenCV (`opencv-python`) is used for image encoding and some image-dependent
display helpers. In many setups it is available transitively via OCR
dependencies, but if your environment lacks it you may see missing
overlay/preview behavior.

Install (optional):

```bash
uv add opencv-python
```

Troubleshooting
---------------

- Blank Overlays: Ensure images are valid and readable;
  check logs for OCR/loader errors. Missing OpenCV is usually fine.
- No Pages Loaded: Confirm the project directory path is correct and contains supported image extensions.
- Ground Truth Not Showing: Verify `pages.json` is valid JSON and keys match
  filenames (case insensitive); restart or click Open again.
- Import Path Errors: Make sure `pd-book-tools` is cloned sibling to this
  project root so the relative path source defined in `pyproject.toml`
  resolves.
- Environment Issues: Try `make reset` to rebuild the virtual environment,
  or `make reset-full` for a complete reset including UV cache.

Development Workflow
--------------------

Makefile Commands
-----------------

The project includes a Makefile with convenient development commands:

```bash
make help        # Show all available commands
make install     # Install dependencies and set up pre-commit hooks
make test        # Run pytest test suite
make lint        # Run ruff linting checks with fixes
make format      # Format code with ruff
make clean       # Clean cache files and temporary artifacts
make reset       # Rebuild virtual environment (keeps UV cache)
make reset-full  # Nuclear reset: clear all caches and redownload
make release-patch  # Bump patch version, commit, and tag
make release-minor  # Bump minor version, commit, and tag
make release-major  # Bump major version, commit, and tag
```

Running Tests
-------------

```bash
make test
```

For targeted runs, use `uv run pytest -n auto ...` (for example `make test-k K='pattern'` or `uv run pytest -n auto tests/path/to/test_file.py`).

Browser-Based Regression Tests
------------------------------

Use the browser test target to validate core UI rendering in a real browser context:

```bash
make test-browser
```

Browser tests are marked with `@pytest.mark.browser` and run via:

```bash
make test-browser
```

One-time local setup for Playwright Chromium binaries
(required to execute, not skip):

```bash
uv run playwright install chromium
```

Notes:

- Chromium is required for browser tests and is installed by `make install`.
- If Chromium cannot be launched, browser tests fail fast with a setup error.

Code Quality
------------

```bash
make lint        # Lint and auto-fix issues
make format      # Format code
make pre-commit-check  # Run pre-commit hooks on all files
```

Releasing
---------

Use the Makefile release targets to bump version, create a release commit,
and create a matching git tag:

```bash
make release-patch  # 0.1.0 -> 0.1.1
make release-minor  # 0.1.0 -> 0.2.0
make release-major  # 0.1.0 -> 1.0.0
```

Each target will:

- Run `uv version --bump ...`
- Stage `pyproject.toml` and `uv.lock`
- Create commit: `chore: release vX.Y.Z`
- Create tag: `vX.Y.Z`

Then push the release:

```bash
git push && git push --tags
```

Development Notes
-----------------

- See `docs/planning/README.md` for roadmap & phased feature list.
- `AppState` in `pd_ocr_labeler/state/app_state.py` handles app-level project
  discovery/selection and session notifications.
- `ProjectState` in `pd_ocr_labeler/state/project_state.py` handles page
  navigation, lazy OCR loading, page persistence, and bulk save.
- `PageState` in `pd_ocr_labeler/state/page_state.py` handles per-page image
  caching and word style tracking.
- ViewModel layer (`pd_ocr_labeler/viewmodels/`) provides MVVM binding between
  state and NiceGUI views.
- Operations layer (`pd_ocr_labeler/operations/`) contains business logic for
  persistence, OCR processing, export, and word/line operations.
- UI composition lives in modular components under `pd_ocr_labeler/views/`.
- Minimal wrapper `NiceGuiLabeler` is in `pd_ocr_labeler/app.py`.

Future Enhancements (Short List)
--------------------------------

- Multi-JSON project file merge with page index offsets
- Full persistence metadata schema and session restore
- Derived word/line cache optimization
- GPU backend strategy and distribution packaging

License
-------

No project license has been published yet.
