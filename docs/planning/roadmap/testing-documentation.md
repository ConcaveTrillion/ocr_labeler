# Roadmap Phase 7: Testing and Documentation

**Priority:** Medium
**Status:** In Progress

## Completed

- Playwright browser test infrastructure (`tests/browser/`)
- Browser regression tests for word match editing workflows
- Word match unit tests (`tests/views/projects/pages/test_word_match.py`)
- Markdown linting via `markdownlint-cli2` (pre-commit hook + `make md-lint`)
- 15+ browser test modules covering: smoke, home page, project loading,
  navigation, image tabs, text tabs, session isolation, page actions,
  word match, line/paragraph/page/word toolbar actions, word edit dialog,
  source folder dialog, keyboard shortcuts
- Log handler isolation for parallel test execution (conftest fixture)
- Reusable browser test helpers with `data-testid` selector patterns
- **14-commit browser test coverage plan fully executed** — 97% of 107 UI
  buttons now have browser test coverage (`make test-browser` passes:
  157 passed, 2 data-conditional skips)

## Coverage Status

- **~97% of 107 UI buttons** have browser test coverage
- Paragraph toolbar fully tested (9/9 buttons, 100%)
- Navigation controls fully tested
- Word edit dialog operations (merge/split/crop/refine/nudge): 100%
- Source folder dialog: 100%
- Keyboard shortcuts and GT text input editing: covered
- Show Lines/Words checkboxes and selection-mode radios: covered

## Scope (Remaining)

- ~~Save/load round-trip tests~~ (Done — 12 unit tests covering structure,
  word attributes, original page, and edge cases; browser-level round-trip
  tests still pending)
- Filtering behavior tests
- README refresh and developer/troubleshooting docs (partially done)
