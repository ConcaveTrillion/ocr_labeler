# CLAUDE — pd-ocr-labeler

NiceGUI web app for reviewing and correcting OCR output. Displays page images
with overlays; lets users edit words/lines/paragraphs, tag styles, and save
corrections as ground truth. Depends on `pd-book-tools` for OCR and
page-model primitives.

## Commands

| target | does |
| --- | --- |
| `setup` | dev venv + pre-commit + Playwright |
| `install` | `uv tool install` (puts `pd-ocr-labeler-ui` on PATH) |
| `test` | `uv run pytest -n auto` |
| `test-k K='pat'` | targeted pytest with `-n auto` |
| `test-single TEST='...'` | single test file/function |
| `test-browser` | Playwright browser regression tests |
| `lint` / `lint-fix` | ruff + markdownlint (with --fix) |
| `format` | ruff format |
| `build` | build wheel |
| `run` | start the app |
| `ci` | format + lint + test |
| `coverage` | coverage report |
| `clean-cache` / `clean-logs` | clear page-image cache / runtime logs |

Append `AI=1` to any target for agent-friendly output — verbose output is
captured to `.ci-ai.log`; stdout shows `✅ <target> passed` on success or
filtered failure sections on error. Works for every target: `make ci AI=1`,
`make test AI=1`, etc.

Always include `-n auto` on pytest invocations.

## Rules

- Make targets first; fall back to `uv run …` only when no target exists.
- Never `python -m pytest` / `python3 -m pytest`. Always `uv run pytest -n auto`
  or `make test` (include `-n auto`). Bare `python`/`python3`/`.venv/bin/python`
  miss the venv.
- NiceGUI async: use `background_tasks.create(…)` for background work and
  `run.io_bound(…)` for blocking I/O. Never `asyncio.create_task`,
  `loop.run_in_executor`, or `asyncio.to_thread` in app code.
- Do not silently swallow recoverable exceptions in UI/navigation flows.
  Log with context and surface a user-visible notification when behavior
  degrades but the app can continue.
- `pd-book-tools` is pinned in `pyproject.toml`; use a `uv.toml` (gitignored)
  with `[tool.uv.sources]` override for local-dev against a sibling checkout —
  see `DEVELOPMENT.md`.
- Run `make lint` after editing any Markdown under `docs/`.

## Runtime logs

Per-session log files: `session_<YYYYMMDD>_<HHMMSS>_<pid>.log` under the
OS-aware app data root (`PersistencePathsOperations.get_logs_root()`).

| OS      | Default log directory                                                               |
| ------- | ----------------------------------------------------------------------------------- |
| Linux   | `$XDG_DATA_HOME/pd-ocr-labeler/logs` (default `~/.local/share/pd-ocr-labeler/logs`) |
| macOS   | `~/Library/Application Support/pd-ocr-labeler/logs`                                 |
| Windows | `%APPDATA%/pd-ocr-labeler/logs`                                                     |

Dev container: `/home/vscode/.local/share/pd-ocr-labeler/logs/`. Most recent
session = latest mtime (`ls -lat`).

Other runtime paths (same `get_*_root()` helpers):

- Page image cache: `$XDG_CACHE_HOME/pd-ocr-labeler/page-images`
- Saved labeled projects: `<data root>/pd-ocr-labeler/labeled-projects`

## Sibling repos

- `../pd-book-tools/` — upstream dependency.
