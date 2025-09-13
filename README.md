OCR Labeler (NiceGUI UI)
========================

Minimal web UI for navigating OCR page images, viewing overlays, and comparing OCR output with ground truth text. Built with [NiceGUI](https://nicegui.io/) and a lightweight state layer that lazily loads and OCRs pages via `pd-book-tools`.

Current Capabilities
--------------------
- Open a project directory containing page images (`.png`, `.jpg`, `.jpeg`).
- Auto–lazy load & OCR each page the first time you navigate to it.
- Navigate pages (Prev / Next / direct page number input).
- Display multiple overlay variants (original, paragraphs, lines, words, mismatches – where available from the underlying OCR lib).
- Show read‑only OCR text and (optional) ground truth text side by side.
- Auto‑populate ground truth text from an optional `pages.json` file mapping image filename -> ground truth string.

Planned / Not Yet Implemented (see `TODOs.md` for full roadmap)
--------------------------------------------------------------
- Editing & saving OCR / word‑level adjustments
- Bounding box refinement & bulk operations
- Training / validation export
- Word split / merge / crop tools
- Line & word validation workflows

Quick Start
-----------

### 1. Prerequisites
- Python 3.13+ (project is configured with `requires-python = ">=3.13"`).
- [uv](https://github.com/astral-sh/uv) recommended for fast, locked installs (a `uv.lock` is included).
- Optional: `opencv-python` (NiceGUI image overlays will still attempt a fallback cache approach if OpenCV encoding isn't available, but having it improves in‑memory PNG encoding speed). If not already present, install it manually (see Extras below).

### 2. Clone Repositories
This project depends on `pd-book-tools` via a relative path (configured in `pyproject.toml`). Place both repos side‑by‑side:

```
parent_dir/
	pd-book-tools/
	ocr_labeler/   (this repo)
```

Example:
```bash
git clone https://github.com/your-org/pd-book-tools.git
git clone https://github.com/your-org/ocr_labeler.git
cd ocr_labeler
```

### 3. Install Dependencies
Using uv (preferred):
```bash
uv sync
```

Or ad‑hoc run without a full sync (will resolve on the fly):
```bash
uv run python -c "import nicegui"
```

### 4. Prepare a Project Directory
Create (or choose) a folder with page images you want to inspect, e.g.:
```
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

### 5. Run the UI (CLI)
A console entrypoint `ocr-labeler-ui` is installed.

Basic launch (replace `sample_project` with your images directory):
```bash
uv run ocr-labeler-ui sample_project
```

Change host/port (e.g. access from another device on LAN):
```bash
uv run ocr-labeler-ui sample_project --host 0.0.0.0 --port 9000
```

Disable auto project load (open via UI after startup):
```bash
uv run ocr-labeler-ui sample_project --no-auto-load
```

Increase logging verbosity:
```bash
uv run ocr-labeler-ui sample_project -v        # info
uv run ocr-labeler-ui sample_project -vv       # debug
```

Then open: http://127.0.0.1:8080/ (or your chosen host/port)

### 6. Using the Interface
1. Project Directory: Confirm (or edit) the path shown, then click Open.
2. Navigation: Use Prev / Next or type a page number (press Enter or defocus field).
3. Tabs (left): Switch between overlay variants; a single central spinner shows while a page is loading.
4. Tabs (right): View Ground Truth vs OCR text. Ground truth is blank if not found in `pages.json`.

Custom Fonts (Optional)
-----------------------
`NiceGuiLabeler` accepts `monospace_font_name` and `monospace_font_path`. At present the font file isn't auto‑injected into the DOM (future enhancement); supplying a path is forward‑compatible for when that feature lands.

Example future usage (will not break now):
```python
NiceGuiLabeler(project_root, monospace_font_name="MyMono", monospace_font_path=Path("fonts/MyMono.ttf"))
```

OpenCV Optional Dependency
--------------------------
If OpenCV (`opencv-python`) is installed, the app encodes overlay images in‑memory for faster display. Without it, a disk cache fallback is used.

Install (optional):
```bash
uv add opencv-python
```

Troubleshooting
---------------
- Blank Overlays: Ensure images are valid and readable; check logs for OCR/loader errors. Missing OpenCV is usually fine.
- No Pages Loaded: Confirm the project directory path is correct and contains supported image extensions.
- Ground Truth Not Showing: Verify `pages.json` is valid JSON and keys match filenames (case insensitive); restart or click Open again.
- Import Path Errors: Make sure `pd-book-tools` is cloned sibling to this project root so the relative path source defined in `pyproject.toml` resolves.

Development Notes
-----------------
- See `TODOs.md` for roadmap & phased feature list.
- `AppState` in `ocr_labeler/state/app_state.py` handles navigation + lazy OCR.
- UI composition lives in modular components under `ocr_labeler/views/`.
- Minimal wrapper `NiceGuiLabeler` is in `ocr_labeler/app.py`.

Future Enhancements (Short List)
--------------------------------
- Save / load edited OCR JSON
- Word / line granular editing and validation
- Bounding box refinement & regeneration
- Training / validation dataset export

License
-------
TBD (add license details here).
