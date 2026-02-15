# Architecture Doc Sync Tasks

Small, low-context tasks for reconciling docs with code. Do only a few at a time.

- [x] Refresh architecture index with current module map (`docs/architecture/README.md`)
- [x] Revalidate async affected-file paths (`docs/architecture/async/affected-files.md`)
- [x] Capture current view/state/viewmodel boundaries in docs
- [x] Verify `docs/architecture/multi-tab/*` claims against `ocr_labeler/app.py` session setup
- [x] Verify `docs/architecture/async/migration-patterns.md` examples against current APIs
- [x] Verify `docs/architecture/threading-architecture.md` against OCR and persistence call paths
- [x] Add a brief “last validated” date to each architecture doc after review

Suggested workflow:

1. Pick 1-2 unchecked items.
2. Validate paths and behavioral claims directly in code.
3. Apply minimal doc edits only.
4. Run `Make: CI Pipeline` when code changes are included.
