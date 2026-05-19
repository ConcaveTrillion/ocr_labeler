# Browser-test selection helpers — deep review (iter 34)

Scope of this review: the per-file private helpers used to select
words / lines / paragraphs across `tests/browser/` and how they
combine to express multi-word and multi-line selection scenarios in
iters 19-24's split-family coverage. Triggered by iter 33's
recommended pivot path when the Cancel-revert-mechanism browser test
turned out to be infeasible (Quasar removes `q-dialog` children from
the DOM on close, so the input value cannot be inspected mid-close).

## What's in `tests/browser/helpers.py` today

The shared helpers module exposes:

- `wait_for_app_ready(page, timeout=30_000)` — waits for the
  "Project" label to be visible.
- `wait_for_page_number(page, expected, timeout=30_000)` — polls
  `nav-page-input` until it has the expected value.
- `load_project(page, project_name, timeout=60_000)` — opens the
  Quasar select, picks a project, clicks LOAD, waits for the
  loading overlay to hide and `nav-next-button` to appear.
- `wait_for_page_loaded(page, timeout=60_000)` — waits for the
  "Layers" text (page content rendered).
- `navigate_to_page(page, page_number, timeout=60_000)` — fills
  `nav-page-input` and clicks `nav-goto-button`.
- `get_current_page_number(page)` /
  `get_page_total_text(page)` — read accessors.

Notable absences: there is **no shared selection helper**. Every
test file that needs to "select word N" or "select line N" or "wait
for a Quasar notification" or "switch to All Lines view" reimplements
the same primitive in private form.

## Duplicated private helpers across test files

The following private helpers are reimplemented (sometimes verbatim)
in several files:

| Helper | Files reimplementing it |
| --- | --- |
| `_setup(page, url)` | `test_word_match.py`, `test_toolbar_word_actions.py`, `test_toolbar_paragraph_actions.py`, `test_toolbar_line_actions.py`, `test_toolbar_page_actions.py`, `test_word_match_line_actions.py`, `test_word_edit_dialog.py`, `test_keyboard_shortcuts.py`, `test_page_actions.py`, `test_source_folder_dialog.py`, `test_ocr_config_modal.py` (11 files) |
| `_switch_to_all_lines(page)` | `test_toolbar_word_actions.py`, `test_toolbar_paragraph_actions.py`, `test_toolbar_line_actions.py`, others (multiple) |
| `_wait_for_notification(page, timeout=15_000)` | `test_toolbar_word_actions.py`, `test_toolbar_paragraph_actions.py`, `test_toolbar_line_actions.py`, others |
| `_select_word(page, index=0)` | `test_toolbar_word_actions.py`, `test_toolbar_line_actions.py` (verbatim duplicate) |
| `_select_line(page, index=0)` | `test_toolbar_line_actions.py` |
| `_select_paragraph(page, index=0)` | `test_toolbar_paragraph_actions.py` |
| `_select_first_word(page)` | `test_word_match.py` (variant: doesn't take index, hardcodes `.first`) |
| `_get_gt_inputs(page)` | `test_toolbar_word_actions.py`, `test_toolbar_paragraph_actions.py`, `test_toolbar_line_actions.py` |
| `_get_ocr_labels(page)` | `test_toolbar_word_actions.py`, `test_toolbar_paragraph_actions.py`, `test_toolbar_line_actions.py` |

This is roughly **11 copies of `_setup`**, ~3-5 copies of each
selection helper, and ~3 copies of `_get_gt_inputs` /
`_get_ocr_labels`. Net: hundreds of lines of duplicated test glue.

### Why this matters beyond DRY

1. **Inconsistent timeouts and sleeps.** `_select_word` in
   `test_toolbar_word_actions.py` and `test_toolbar_line_actions.py`
   use `page.wait_for_timeout(1000)` after clicking; `_select_first_word`
   in `test_word_match.py` does the same. But other selection points
   in tests use `wait_for_timeout(500)` (e.g., the inline ctrl+click
   tests in `test_word_match.py`). Inconsistent post-click settling
   delays mean a flake fix in one file doesn't propagate.
2. **Inconsistent locator strategy.** `_select_line` uses
   `page.get_by_label("Select line", exact=True)` (accessibility
   label) while `_select_word` uses `WORD_CHECKBOX` testid. This
   asymmetry is invisible when reading a single test but is real
   coupling to UI implementation choices that have drifted.
3. **Drift risk.** When a notification format changes, the team has
   to update N copies of `_wait_for_notification`. When the
   "All Lines" toggle is renamed, N copies of `_switch_to_all_lines`
   need to change. So far this hasn't been a problem, but the
   surface area is growing iter-by-iter.

## How iters 19-24 expressed multi-word / multi-line selection

### Iter 19 — `test_line_split_after_word`

Single-word selection via `_select_word(page, 0)`. The split-after
operation requires exactly one word selected; the helper's flat-list
indexing was sufficient. No multi-word machinery needed.

### Iter 20 — `test_line_split_by_selection`

Same single-word selection (`_select_word(page, 0)`). The
split-by-selection operation enables on `>= 1 word selected`, so the
single-word degenerate case is testable with the existing helper.
The test asserts a `+1` line delta — the same observable that
`test_line_split_after_word` would produce, which is why iter 21
flagged this as the weakest link in the split-family coverage.

### Iter 22 — `test_line_split_by_selection_cross_line`

Cross-line selection. Here the flat-list `_select_word(page, N)`
helper became insufficient: there's no helper-level abstraction for
"select line K, word J" given that word checkboxes are flat-listed
across all lines in DOM order. The test computes the global
flat-list index of `(line_1, word_0)` by counting word-checkboxes
that precede `line-delete-button[1]` in DOM order via
`page.evaluate(...)` JavaScript. **This is hand-rolled, in-test.**
It's a real DOM traversal expressed inline rather than as a helper,
because nobody else needed it yet.

### Iter 24 — `test_line_split_by_selection_non_contiguous`

Non-contiguous within-line selection (words 0 and 2, skipping word
1). Same approach as iter 22: a `page.evaluate` block computes
"line 0's word count" by counting word-checkboxes that precede
`line-delete-button[1]`. The test then calls
`_select_word(page, 0)` and `_select_word(page, 2)` against the
flat list. **Inline JS again.** The two `page.evaluate` blocks in
iters 22 and 24 share substantial logic but were copy-pasted with
small changes.

### Iters 19-21 also produced a review note

`docs/review-notes/2026-05-06-toolbar-split-family.md` exists from
iter 21 and ranked the distinguishing-coverage gaps that iters 22
and 24 then closed. The review correctly identified the cross-line
and non-contiguous gaps; what it didn't surface was that **the test
infrastructure (helpers) was missing the per-line-keyed selection
primitive** that those tests then had to build inline.

## What's missing

A genuinely useful helper would be `select_word(page, line_index,
word_index)` that internally maps `(L, W)` to the global flat-list
index by walking DOM. The two `page.evaluate` blocks in
`test_toolbar_line_actions.py` already implement most of this — they
just stop at "give me one specific global index" rather than
"give me a coordinate-to-flat-index map." Lifting them into
`helpers.py` as `flat_index_for_line_word(page, line_index,
word_index)` would let future split-family or multi-selection tests
write `select_word(page, 0, 0)` and `select_word(page, 1, 0)`
without inline JavaScript.

A second missing primitive: `select_words_by_line_word(page,
[(0, 0), (0, 2)])` for non-contiguous selection. Useful for
iter 24's pattern and for any future "selected words from N lines"
scenarios.

## Ranked follow-ups

These are pure test-infrastructure work — no production code
changes — and **safe overnight**:

1. **(High value, low risk)** Move `_setup`, `_switch_to_all_lines`,
   `_wait_for_notification`, `_select_word(page, index)`,
   `_select_line(page, index)`, `_select_paragraph(page, index)`,
   `_get_gt_inputs`, `_get_ocr_labels` into `tests/browser/helpers.py`
   under public names. Update the 11 test files to import them.
   Rename `_select_first_word` to `select_word(page, 0)` and inline.
   Caveat: this is a large diff (touches every browser test file)
   and should land as one PR — do not split.
2. **(Medium value, low risk)** Add
   `flat_index_for_line_word(page, line_index, word_index)` as a
   helper, lifting the inline `page.evaluate` from
   `test_toolbar_line_actions.py:533-552`. Then add a
   `select_word_by_line_word(page, line_index, word_index)`
   convenience that calls the existing single-arg `select_word`
   with the computed index. Refactor the two existing tests
   (cross-line, non-contiguous) to use it.
3. **(Lower value, higher risk)** Audit the 162 `wait_for_timeout`
   calls across browser tests for replaceability with `expect(...)`
   or `wait_for(state=...)` patterns. Each `wait_for_timeout` is a
   hard sleep — replacing with assertion-driven waits removes
   fragility. But each replacement has to be evaluated case-by-case
   and the safest ones are inside the helpers we'd already
   centralize in (1).
4. **(Open question, audit only)** The
   `test_word_ctrl_click_multi_select` and
   `test_word_ctrl_click_deselect` tests use
   `click(modifiers=["ControlOrMeta"])` against plain Quasar
   checkboxes. For checkboxes the modifier flag has no effect on
   default browser semantics — checking checkbox B doesn't uncheck
   checkbox A whether ctrl is held or not. So these tests may pass
   identically with or without the modifier, in which case they're
   not actually testing a ctrl-click contract. Worth a closer read
   of the underlying word-checkbox click handler in
   `pd_ocr_labeler/views/word_match/...` to confirm whether there's
   a real ctrl-click branch being exercised, or whether the tests
   are tautological. Production-code-touching follow-up if they're
   tautological.

## Blockers needing the human

- Item 1's refactor is purely additive but spans 11 files. It needs
  a single human-approved review pass, not overnight churn (the
  review-able diff is large enough to warrant intent confirmation
  before landing).
- Item 4 may surface a tautological test that requires either a
  production-code clarification or a test rewrite. Either path
  needs the user.
- Items 2 and 3 are safe to attempt overnight in small increments
  if no other priorities surface, but iter 35+ should pick from
  iter 33's queued top-3 first (atomic `apply_ocr_config` command,
  negative-path Apply browser test) before consuming this list.

## Appendix — files inspected

- `tests/browser/helpers.py`
- `tests/browser/test_word_match.py`
- `tests/browser/test_toolbar_word_actions.py`
- `tests/browser/test_toolbar_line_actions.py`
- `tests/browser/test_toolbar_paragraph_actions.py`
- `tests/browser/test_ocr_config_modal.py`
- `pd_ocr_labeler/views/header/ocr_config_modal.py`
  (re-read for the abandoned candidate-3 attempt)
