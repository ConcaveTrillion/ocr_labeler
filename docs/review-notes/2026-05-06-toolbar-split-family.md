# Toolbar Split Family — Code Review

Iter 21 of the overnight `/loop`.  The iter-21 task plan queued
"`line-extract-from-selection-button` click test" as candidate 3; the
pre-flight audit found that the underlying button (the icon wired to
`split_line_with_selected_words_callback`) is **already covered** by
`tests/browser/test_toolbar_word_actions.py::test_word_form_line` via
its real testid `word-form-line-button`.  It is a word-scope toolbar
button, not a line-scope button; the planning doc and prior iter-20
prompt were both wrong about the testid name.

Per the iter-21 prompt's pivot guidance, this note is the deep code
review of the three split-family operations, to confirm they are
distinct (not aliases) and to record the precise contract of each.

## The three operations

There are three load-bearing toolbar buttons in this family.  All three
ultimately mutate `Page` lines via `pd-book-tools` primitives, but each
expresses a different intent and a different selection contract.

**Button A — `line-split-after-word-button`**

- Scope row: Line
- Enable rule: callback present AND exactly 1 word selected
- UI handler (`word_match_actions.py`): `_handle_split_line_after_selected_word`
- View callback attr: `split_line_after_word_callback`
- `PageState` method (this repo): `split_line_after_word(line_index, word_index)`
- `pd-book-tools` primitive (`Page.*`): `split_line_after_word(line_index, word_index)`

**Button B — `line-split-by-selection-button`**

- Scope row: Line
- Enable rule: callback present AND >= 1 word selected
- UI handler: `_handle_split_lines_into_selected_unselected_words`
- View callback attr: `split_lines_into_selected_unselected_callback`
- `PageState` method: `split_lines_into_selected_and_unselected_words(keys)`
- `pd-book-tools` primitive: `split_lines_into_selected_and_unselected_words(keys)`

**Button C — `word-form-line-button` ("extract")**

- Scope row: Word
- Enable rule: callback present AND >= 1 word selected
- UI handler: `_handle_split_line_by_selected_words`
- View callback attr: `split_line_with_selected_words_callback`
- `PageState` method: `split_line_with_selected_words(keys)`
- `pd-book-tools` primitive: `split_line_with_selected_words(keys)`

## Are these distinct, or aliases?

**Distinct.**  They share family resemblance but differ in three
load-bearing dimensions:

### 1. Scope row

`split_line_after_word` is rendered in the *line-scope* row of the
toolbar.  The other two are rendered alongside other word-scope verbs
(`merge`, `delete`, `form-line`, `form-paragraph`).  The scope row
visually communicates "this verb consumes selected lines/words" — and
in fact `split_line_after_word` requires a *line* selection in spirit,
even though its enable rule reads the *word* selection (because it
needs both indices).

### 2. Selection contract

- `split_line_after_word`: **exactly one word selected.**  Disabled
  for 0 or >=2 selections.  Picks the unique `(line, word)` from the
  selection.
- `split_line_by_selection` and `extract_line_from_selection`
  (`form-line`): **>=1 word selected.**  Both accept the entire
  `selected_word_indices` set.

### 3. Output topology — for the same input, the lines look different

Concrete six-word page with one line `[a, b, c, d, e, f]`:

- **Split-after-word** with word `c` (index 2) selected →
  two lines: `[a, b, c]` and `[d, e, f]`.  Cut point sits *after* the
  selected word; the selected word is in the *first* line.
- **Split-by-selection** with words `b, d` selected →
  two lines: `[b, d]` (selected partition) and `[a, c, e, f]`
  (unselected partition).  Order within each partition is preserved
  but words are no longer contiguous on the page.
- **Extract-line-from-selection** ("form line") with words `b, d`
  selected → two lines: `[a, c, e, f]` (residual) and `[b, d]`
  (extracted into a *new* line).  Same two-partition output as
  split-by-selection!  The semantic difference shows up only when the
  selection spans multiple source lines:

  - `split_lines_into_selected_and_unselected_words` produces *two*
    output lines *per affected source line* (selected/unselected
    partition of each).
  - `split_line_with_selected_words` produces *one* output line
    (containing all selected words across all source lines), plus
    leaves residual unselected words in their original lines.

  So with selection `{(0, 1), (1, 0)}` on a page where line 0 is
  `[a, b, c]` and line 1 is `[d, e]`:

  - split-by-selection → `[a, c]` + `[b]` + `[e]` + `[d]` (4 lines:
    each source line splits in two).
  - extract-line-from-selection → `[a, c]` + `[d, e]` (residuals,
    2 lines remain) + `[b, d]` (one new line containing selected
    words from both sources) = 3 lines.

This per-line vs cross-line distinction is the load-bearing reason
both buttons exist.  For the degenerate single-line single-word case
they collapse to identical output (selected word becomes its own
line; residue stays together; net +1 line) — which is exactly what
the existing `test_word_form_line` and `test_line_split_by_selection`
both assert.

### Single-word selection is a degenerate case

For 1 word selected on a multi-word line, **all three operations
produce +1 line** with the selected word in one of the two output
lines.  They differ only in which line gets the prefix/suffix:

- split-after-word with word `i` selected on `[w_0, ..., w_n]`:
  `[w_0..w_i]` + `[w_{i+1}..w_n]` (selected word is *last in first
  line*; only valid if `i < n`).
- split-by-selection with `{(line, i)}`: `[w_i]` + `[w_0..w_n] \ [w_i]`
  (selected word is alone in one line).
- extract-line-from-selection with `{(line, i)}`: residue
  `[w_0..w_n] \ [w_i]` plus a new line `[w_i]` (selected word is
  alone in a new line — same output topology as split-by-selection
  on a single line, just a different notification copy and different
  toolbar location).

This is why iters 19/20 and the existing `test_word_form_line` all
assert `+1` line.  It is the right invariant for the degenerate path,
but it does *not* exercise the genuinely distinguishing logic.

## Test coverage matrix

**`line-split-after-word-button`**

- Disabled-without-selection: yes (iter 16)
- Enabled-with-selection: yes (iter 16)
- Tooltip: yes
- Click (single-word, +1 line): yes (iter 19)
- Click (multi-word): n/a (enable rule requires exactly 1)
- Click (cross-line): n/a (enable rule requires exactly 1)

**`line-split-by-selection-button`**

- Disabled-without-selection: yes (iter 16)
- Enabled-with-selection: yes (iter 16)
- Tooltip: yes
- Click (single-word, +1 line): yes (iter 20)
- Click (multi-word): none
- Click (cross-line): none

**`word-form-line-button` ("extract")**

- Disabled-without-selection: yes
- Enabled-with-selection: yes
- Tooltip: yes
- Click (single-word, +1 line): yes (`test_word_form_line`)
- Click (multi-word): none
- Click (cross-line): none

The two highlighted gaps — **multi-word selection on a single line**
and **cross-line selection** — are where the two `>=1`-selection
buttons stop being interchangeable.  Adding click tests that drive
those topologies would be the next genuine increment in coverage,
not yet-another single-word +1 assertion.

## Suggested next-iteration candidates

Listed by leverage / likelihood of catching real regressions.

1. **Cross-line `split-by-selection` click test.**  Select word 0 on
   line 0 *and* word 0 on line 1 (or wherever the fixture supports
   it), click `line-split-by-selection-button`, assert line count
   delta of +2 (two source lines each split into selected/unselected
   pair).  Notification copy: "Split line(s) into selected and
   unselected words".  This is the test that distinguishes
   split-by-selection from extract-line.

2. **Cross-line `extract-line-from-selection` ("form-line") click
   test.**  Same selection as candidate 1, but click
   `word-form-line-button` instead.  Assert line count delta of +1
   (one new line containing both selected words; residuals stay in
   their original lines).  Verifies the per-affected-line vs
   single-output-line distinction.

3. **Multi-word same-line `split-by-selection` click test.**  Select
   words 0 and 2 on a multi-word line (skip word 1), click
   `line-split-by-selection-button`, assert +1 line.  Selected
   partition is `[w_0, w_2]`, unselected is `[w_1, w_3, ...]` — proves
   that the selected partition is *not* required to be contiguous.

These are unblocked by the existing fixture (page 1, 7 lines, 21
words from fresh OCR) and follow the iter 19/20 pattern directly.

## Conclusion

The three split-family buttons are genuinely distinct operations with
different selection contracts and different output topologies.  Aliasing
is not present.  The current browser test suite covers the *enable*
contract and the *single-word degenerate* path for all three; it does
not yet cover the topologies that make split-by-selection and
extract-line distinct from each other.  Iter-21's planned candidate-3
work is therefore complete, with the gap-finding having been the
real iteration product.
