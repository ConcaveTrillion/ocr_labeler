# Developing pd-ocr-labeler

This document covers the developer workflows for `pd-ocr-labeler`.
End-user install / usage docs live under
[`docs/usage/`](docs/usage/README.md). Architecture docs live under
[`docs/architecture/`](docs/architecture/README.md).

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) (Python package + tool manager)
- Python ≥ 3.13 (uv will provision one if needed)
- `git`
- Optional: NVIDIA GPU + CUDA Toolkit for GPU-accelerated OCR (see
  [`docs/usage/installing.md`](docs/usage/installing.md)).

## Quick start

```sh
git clone https://github.com/ConcaveTrillion/pd-ocr-labeler.git
cd pd-ocr-labeler
make setup
```

This syncs the dev deps from `pyproject.toml` (including `pd-book-tools`
at the pinned git tag), installs the Playwright Chromium binaries used
by the browser test suite, and installs pre-commit hooks. You can now
run `make run` (or `uv run pd-ocr-labeler-ui .`) without installing
globally.

## Make targets

`make help` is authoritative. Highlights below.

### HF model prefetch

`make setup` and `make install` end with a `prefetch-models` step that
warms the HF Hub cache for the default OCR detection + recognition
weights and the layout model — about 150 MB total, paid once. First-page
OCR is then a cache hit instead of a multi-minute download surprise.

```sh
NO_PREFETCH=1 make setup     # skip prefetch (offline / restricted networks)
make prefetch-models         # run prefetch on its own
pd-ocr-labeler-prefetch      # same, via console script after `make install`
```

The HF download primitives live in
[`pd_book_tools.hf`](https://github.com/ConcaveTrillion/pd-book-tools)
so the labeler, pd-ocr-cli, and pd-prep-for-pgdp share a single
canonical model-resolution layer.

### GPU / CPU selection

`setup`, `install`, and `upgrade-deps` auto-detect NVIDIA CUDA (via
`nvidia-smi`) and install the matching PyTorch build. Override with
`GPU=`:

```sh
make setup              # auto-detect (default)
make setup GPU=cpu      # force CPU even on a GPU box
make setup GPU=cu124    # force a specific CUDA index tag
```

For dev targets that use `uv sync` (`setup`, `upgrade-deps`), the swap
happens *after* sync via
`uv pip install --reinstall torch torchvision torchaudio
--index-url https://download.pytorch.org/whl/<tag>`. It's idempotent —
if torch already reports a CUDA build, no reinstall happens. For
`install` (which uses `uv tool install`), the CUDA index is passed as
`--extra-index-url` at install time.

### General

| Target | Purpose |
| --- | --- |
| `setup` | Install dev deps + Playwright Chromium + pre-commit hooks (uses pinned `pd-book-tools` tag). Auto-swaps CUDA torch and prefetches HF models. |
| `install` | Install `pd-ocr-labeler-ui` / `pd-ocr-labeler-export` as a `uv tool` from local source, auto-detecting CUDA. |
| `uninstall` | Remove the installed `pd-ocr-labeler` uv tool. |
| `prefetch-models` | Pre-warm the HF cache for default OCR + layout models. |
| `run` / `run-verbose` / `run-page-timing` | Launch the UI against the current directory as the project root. |
| `lint` / `format` | Run ruff (Python) and markdownlint. |
| `pre-commit-check` | Run pre-commit on all files. |
| `test` | Run the pytest suite (parallelized via `pytest-xdist`). |
| `test-k K='pattern'` / `test-single TEST='nodeid'` | Targeted pytest runs. |
| `test-browser` | Run Playwright-backed UI regression tests. |
| `coverage` | Run tests with HTML coverage report. |
| `build` | `uv build` — produce sdist + wheel in `dist/`. |
| `ci` | `setup` → `pre-commit-check` → `test` → `build`. |
| `clean` / `clean-logs` / `clean-cache` | Remove caches, session logs, pre-rendered image cache. |
| `reset` / `reset-full` | Rebuild venv (full also clears the uv cache). |
| `upgrade-deps` | `uv lock --upgrade` + sync. |
| `upgrade-pd-book-tools` | Bump the `pd-book-tools` pin to the latest GitHub tag. |
| `release-{patch,minor,major}` | Bump version in `pyproject.toml`, commit, and tag (push with `git push --tags`). |

### Working against a local pd-book-tools checkout

If you need to develop pd-ocr-labeler against an in-progress
`pd-book-tools` change, drop a `uv.toml` next to `pyproject.toml`
pointing the source at your local checkout, e.g.:

```toml
[tool.uv.sources]
pd-book-tools = { path = "../pd-book-tools", editable = true }
```

`uv.toml` is gitignored. Re-run `make setup` (or `uv sync --group all-dev`)
to apply the override; remove the file to revert to the pinned tag.

## Runtime paths

Per-session log files are written as
`session_<YYYYMMDD>_<HHMMSS>_<pid>.log` under the OS-aware app data
root, resolved by `PersistencePathsOperations.get_logs_root()` in
[`persistence_paths_operations.py`](pd_ocr_labeler/operations/persistence/persistence_paths_operations.py).

| OS | Default log directory |
| --- | --- |
| Linux | `$XDG_DATA_HOME/pd-ocr-labeler/logs` (default `~/.local/share/pd-ocr-labeler/logs`) |
| macOS | `~/Library/Application Support/pd-ocr-labeler/logs` |
| Windows | `%APPDATA%/pd-ocr-labeler/logs` (default `%USERPROFILE%/AppData/Roaming/pd-ocr-labeler/logs`) |

Other useful runtime paths (same `get_*_root()` helpers):

- Page image cache: `$XDG_CACHE_HOME/pd-ocr-labeler/page-images`
  (cleared by `make clean-cache`).
- Saved labeled projects:
  `<data root>/pd-ocr-labeler/labeled-projects`.
- Logs cleanup: `make clean-logs`.

## Validation rules

- Always use `uv` to run tests — never `.venv/bin/python`,
  `python -m pytest`, or `python3 -m pytest`.
- Prefer Make targets (`make test`, `make ci`, `make test-k`,
  `make test-single`); they already include `-n auto` for parallel
  execution.
- After code changes, run `make ci` (or the VS Code "Make: CI Pipeline"
  task).
- Docs-only changes can skip CI but should pass `make lint`
  (markdownlint runs there).

See [`AGENTS.md`](AGENTS.md) for the full validation policy
agents must follow.

## Releasing

1. Make sure the `pd-book-tools` pin in `pyproject.toml` matches the
   intended release. `make upgrade-pd-book-tools` bumps to latest tag.
2. Run `make ci` to lint + test + build cleanly.
3. Tag and push:

   ```sh
   make release-minor   # or release-patch / release-major
   git push && git push --tags
   ```

   `release-*` bumps the version in `pyproject.toml`, creates a
   `chore: release vX.Y.Z` commit, and tags `vX.Y.Z`. It does **not**
   push.

4. The published `install.sh` resolves the latest GitHub tag at install
   time, so end users get the new release on their next `curl | sh`.
