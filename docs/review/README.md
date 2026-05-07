# pd-ocr-labeler Deep Code Review — 2026-05-06

Full module-by-module review of the application. Produced by three parallel review agents
covering all ~50 source files. Intended as a working brief for iterative fixes.

## Documents

| File | Contents |
|---|---|
| [bugs.md](bugs.md) | Crash bugs, correctness bugs, memory leaks — with file:line citations |
| [dead-code.md](dead-code.md) | Unused classes, methods, and constants ready to delete |
| [architecture.md](architecture.md) | Structural / layering issues, god classes, duplication |
| [module-ratings.md](module-ratings.md) | Per-file quality ratings with primary reason |
| [iteration-plan.md](iteration-plan.md) | Prioritised action list for Opus to work through |

## Scope Covered

- **Top-level**: `app.py`, `cli.py`, `constants.py`, `prefetch.py`, `routing.py`, `local_state_cleanup.py`
- **Models**: all of `models/`
- **State**: all of `state/`
- **Services**: all of `services/`
- **Operations**: all of `operations/ocr/`, `operations/persistence/`, `operations/export/`, `operations/validation/`
- **ViewModels**: all of `viewmodels/`
- **Views**: all of `views/`

## Quick Stats

- Files reviewed: ~50
- Critical bugs (crash / data corruption / always-wrong): 6
- Memory leaks: 2
- Correctness bugs: 10
- Dead code modules: 8 distinct items
- Architectural issues: 12 categories
- Files rated 1–2/5: 16
