# Roadmap Phase 7: Testing and Documentation

**Priority:** Medium
**Status:** In Progress

## Completed

- Playwright browser test infrastructure (`tests/browser/`)
- Browser regression tests for word match editing workflows
- Word match unit tests (`tests/views/projects/pages/test_word_match.py`)
- Markdown linting via `markdownlint-cli2` (pre-commit hook + `make md-lint`)
- 15 browser test modules covering: smoke, home page, project loading,
  navigation, image tabs, text tabs, session isolation, page actions,
  word match, line/paragraph/page/word toolbar actions, word edit dialog
- Log handler isolation for parallel test execution (conftest fixture)
- Reusable browser test helpers with `data-testid` selector patterns

## Coverage Status

- **28% of 107 UI buttons** have browser test coverage (30/107)
- **14-commit phased plan** targeting 97% coverage
  ([browser-ui-test-plan.md](../browser-ui-test-plan.md))
- Paragraph toolbar fully tested (9/9 buttons, 100%)
- Navigation controls mostly tested (3/4 buttons, 75%)

### Highest-Priority Coverage Gaps

- Toolbar scope actions (line + word rows): 0% coverage
- Word edit dialog operations (merge/split/crop/refine/nudge): 0% coverage
- Per-line action buttons (GT→OCR, Validate, Delete): 0% coverage
- Source folder dialog: 0% coverage
- Header/load controls: 11% coverage

## Scope (Remaining)

- Execute 14-commit browser test coverage plan
- Save/load round-trip tests
- Filtering behavior tests
- README refresh and developer/troubleshooting docs (partially done)
