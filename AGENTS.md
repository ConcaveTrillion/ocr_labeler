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

## Validation rules

- Do not run pytest directly when `make test` exists.
- After code changes, run CI pipeline (`make ci` or VS Code `Make: CI Pipeline`).
- Docs-only changes can skip CI.
- Keep tests aligned with the existing structure in `tests/`.

## NiceGUI async guardrails

- Use `background_tasks.create(...)` for background async work.
- Use `run.io_bound(...)` for blocking I/O.
- Avoid `asyncio.create_task`, `loop.run_in_executor`, and `asyncio.to_thread` in app code.

## Documentation hygiene

- Update relevant docs when implementation changes architecture or roadmap behavior.
- Prefer updating doc indexes when adding new topical docs.
- Avoid duplicating long architecture/roadmap guidance in instruction files.

## Practical compatibility note

- Many agents discover root-level policy files like `AGENTS.md` and/or `CLAUDE.md`.
- Keep this file as canonical; if needed, create tool-specific wrappers that reference this file.
