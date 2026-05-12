# CLAUDE — pd-ocr-labeler

NiceGUI web app for reviewing and correcting OCR output. Displays page images with
overlays; lets users edit words/lines/paragraphs, tag styles, and save corrections as
ground truth. Depends on `pd-book-tools` for OCR and page-model primitives.

## Commands

| target                   | does                                                 |
| ------------------------ | ---------------------------------------------------- |
| `setup`                  | provision dev venv + pre-commit + Playwright         |
| `install`                | `uv tool install` (puts `pd-ocr-labeler-ui` on PATH) |
| `test`                   | `uv run pytest -n auto`                              |
| `test-k K='pat'`         | targeted pytest with `-n auto`                       |
| `test-single TEST='...'` | single test file/function                            |
| `test-browser`           | Playwright browser regression tests                  |
| `lint`                   | ruff + markdownlint                                  |
| `lint-fix`               | auto-fix lint                                        |
| `format`                 | ruff format                                          |
| `build`                  | build wheel                                          |
| `run`                    | start the app                                        |
| `ci`                     | full check (format + lint + test)                    |
| `coverage`               | coverage report                                      |
| `clean-cache`            | clear page-image cache                               |
| `clean-logs`             | clear runtime logs                                   |

## Rules

- Make targets first; fall back to `uv run …` only when no target exists.
- Never `python -m pytest` or `python3 -m pytest`. Always `uv run pytest -n auto`
  or `make test`. Always include `-n auto`.
- Never `.venv/bin/python`, `python`, or `python3` for project tasks —
  always `uv run …`.
- NiceGUI async: use `background_tasks.create(…)` for background work;
  `run.io_bound(…)` for blocking I/O. Never `asyncio.create_task`,
  `loop.run_in_executor`, or `asyncio.to_thread` in app code.
- Exception handling: do not silently swallow recoverable exceptions in UI/navigation
  flows. Log with context and surface a user-visible notification when behavior
  degrades but the app can continue.
- `pd-book-tools` is pinned in `pyproject.toml`; use a `uv.toml` (gitignored) with
  `[tool.uv.sources]` override for local-dev against a sibling checkout —
  see `DEVELOPMENT.md`.
- Update relevant docs when implementation changes architecture or roadmap behavior.
  Run `make lint` after editing any Markdown under `docs/`.

## Runtime logs

Per-session log files: `session_<YYYYMMDD>_<HHMMSS>_<pid>.log` under the OS-aware
app data root (`PersistencePathsOperations.get_logs_root()`).

| OS      | Default log directory                                                               |
| ------- | ----------------------------------------------------------------------------------- |
| Linux   | `$XDG_DATA_HOME/pd-ocr-labeler/logs` (default `~/.local/share/pd-ocr-labeler/logs`) |
| macOS   | `~/Library/Application Support/pd-ocr-labeler/logs`                                 |
| Windows | `%APPDATA%/pd-ocr-labeler/logs`                                                     |

In this dev container: `/home/vscode/.local/share/pd-ocr-labeler/logs/`.
Most recent session = latest mtime (`ls -lat`).

Other runtime paths (same `get_*_root()` helpers):

- Page image cache: `$XDG_CACHE_HOME/pd-ocr-labeler/page-images`
- Saved labeled projects: `<data root>/pd-ocr-labeler/labeled-projects`

## Sibling repos

- `../pd-book-tools/` — shared OCR/layout/image primitives (upstream dependency).

## Spec lifecycle

Design spec files (`docs/specs/<date>-<topic>-design.md`) live in `docs/specs/` while the
milestone's chore issues are open. When the last chore closes and the implementation ships,
move the file to `docs/architecture/` and commit. See workspace `docs/conventions.md`.
