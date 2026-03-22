# Agent Instructions (Cross-Tool)

Shared instructions for AI coding agents working in this repository (Copilot, Claude Code, and other assistants).

## Scope and precedence

- This file is the cross-agent baseline.
- Tool-specific files (for example `.github/copilot-instructions.md`) should stay thin and point here.
- If a tool requires extra constraints, those are additive and should not duplicate this file.

## Source of truth (read order)

1. `README.md`
2. `docs/architecture/README.md`
3. `docs/planning/README.md`
4. `docs/architecture/nicegui-patterns.md`
5. `docs/architecture/async/overview.md`
6. `docs/architecture/async/migration-patterns.md`

## Workflow and tooling

- Use Makefile targets as the canonical workflow.
- ALWAYS use a Makefile target first when an equivalent target exists.
- ONLY fall back to `uv run ...` when no Make target covers the needed command (for example, highly targeted `pytest -k` runs).
- If running in VS Code, tasks are optional wrappers around Make targets.
- Dependency manager: `uv` (Python `>=3.13`).
- Local non-editable dependency: sibling repo `../pd-book-tools`.

Common commands:

- Install: `make install`
- Test: `make test`
- Lint: `make lint`
- Format: `make format`
- Build: `make build`
- Run app: `make run`
- CI pipeline: `make ci`

## Runtime logs (Linux)

- Linux session/runtime logs are stored under `/home/user/.local/share/pgdp-ocr-labeler/logs`.

## Validation rules

- Always use `uv` to run tests.
- ALWAYS prefer Make targets for validation when they exist (`make test`, `make ci`, `make test-k`, `make test-single`).
- Prefer `make test` / `make ci` for standard validation, and use `uv run pytest ...` for targeted test execution.
- pytest-xdist parallelization is REQUIRED for pytest runs: always include `-n auto`.
- NEVER run project Python commands with `.venv/bin/python`.
- NEVER run project Python commands with `python`.
- NEVER run project Python commands with `python3`.
- ALWAYS run project Python commands through `uv run ...` (or Make targets that already use `uv`).
- NEVER run tests with `.venv/bin/python`.
- NEVER run tests with `python -m pytest`.
- NEVER run tests with `python3 -m pytest`.
- NEVER bypass `uv` for pytest, even for quick one-off checks.
- NEVER suggest direct interpreter pytest commands in examples.
- After code changes, run CI pipeline (`make ci` or VS Code `Make: CI Pipeline`).
- Docs-only changes can skip CI.
- Keep tests aligned with the existing structure in `tests/`.

### Non-negotiable test command policy

- NEVER use `.venv/bin/python -m pytest ...`.
- NEVER use `python -m pytest ...`.
- NEVER use `python3 -m pytest ...`.
- ALWAYS use `uv run pytest ...` or Makefile targets that already call `uv`.
- ALWAYS include `-n auto` on pytest commands (direct or via Make target behavior).
- If a direct-python test command appears anywhere, treat it as policy violation and replace it.

Examples:

- Allowed: `make test` (must run pytest with `-n auto`).
- Allowed: `make test-k K='pattern'` (must run pytest with `-n auto`).
- Allowed: `uv run pytest -n auto -k 'pattern'`.
- Not allowed: `python -m pytest ...`.
- Not allowed: `uv run pytest ...` without `-n auto`.

### Non-negotiable Python executable policy

- NEVER use `.venv/bin/python ...` for project tasks.
- NEVER use `python ...` for project tasks.
- NEVER use `python3 ...` for project tasks.
- ALWAYS use `uv run ...` for Python-based commands.
- If a direct Python executable command appears in guidance, replace it with `uv run ...`.

## NiceGUI async guardrails

- Use `background_tasks.create(...)` for background async work.
- Use `run.io_bound(...)` for blocking I/O.
- Avoid `asyncio.create_task`, `loop.run_in_executor`, and `asyncio.to_thread` in app code.

## Exception handling guardrails

- Do not silently swallow recoverable exceptions in UI/navigation flows.
- Log exceptions with sufficient context and surface a user-visible notification when behavior is degraded but the app can continue.

## Documentation hygiene

- Update relevant docs when implementation changes architecture or roadmap behavior.
- Prefer updating doc indexes when adding new topical docs.
- Avoid duplicating long architecture/roadmap guidance in instruction files.

## Practical compatibility note

- Many agents discover root-level policy files like `AGENTS.md` and/or `CLAUDE.md`.
- Keep this file as canonical; if needed, create tool-specific wrappers that reference this file.
