# Next Step: Per-Word Validation State with Line/Paragraph Rollup

Goal: let users mark individual words as reviewed/validated, with
automatic rollup to line, paragraph, and page level so they can track
labeling progress at every granularity.

## Problem

When labeling a page with many words, there is no way to record which
words have been reviewed and which still need attention.  Users must
mentally track progress or work top-to-bottom every session.  There is
also no persistence — closing and reopening a page loses any notion of
"I already checked these words".

## Desired Behavior

- Each word carries an `is_validated` boolean (default `false`).
- Users can toggle validation per-word from the word-match grid UI.
- **Line rollup:** a line shows as validated when all its words are
  validated.  Partial progress is also visible (e.g. "3/5 validated").
- **Paragraph rollup:** a paragraph shows as validated when all its
  lines are fully validated.
- **Page summary:** page actions bar shows "N / M words validated"
  for at-a-glance progress.
- Validation state survives save/load round-trips.
- Validation is independent of GT matching — a word can be validated
  even if it has a GT mismatch (the user is asserting "I reviewed
  this").

## Implementation Sketch

### Persistence (extend existing `word_attributes` sidecar)

1. **`word_attributes` dict** — add `"validated": true` to the existing
   per-word attribute dict in `UserPagePayload`.  Keys are already
   `"<line_index>:<word_index>"` strings.  No new sidecar field needed —
   validation is just another boolean alongside `italic`, `small_caps`,
   etc.

2. **`_collect_word_attributes` / `_apply_word_attributes_to_page`** —
   extend to read/write `is_validated` on `Word` objects (via
   `word.additional_word_attributes["is_validated"]` or a dedicated
   property if pd-book-tools supports it, otherwise the sidecar handles
   it).

3. No schema version bump needed — existing readers ignore unknown keys
   in `word_attributes` values.

4. **Auto-cache persistence** — validation state must be included in
   auto-save-to-cache writes, not only in explicit "Save Page".  Users
   should not lose validation progress on session reload.  The existing
   `_auto_save_to_cache` path already persists `word_attributes`, so
   including `validated` in that dict means cache saves pick it up for
   free.  Verify that `_auto_save_to_cache` calls
   `_collect_word_attributes` (or equivalent) so validation state is
   captured on every cache write.

### State layer

1. **`PageState`** — add `toggle_word_validated(line_index, word_index)`
   that flips the flag and triggers cache invalidation + notify.
   Optionally add `validate_line(line_index)` and
   `validate_all()` / `clear_all_validation()` bulk helpers.

2. **`WordMatch` model** — surface `is_validated: bool` so the grid can
   bind to it.

3. **`LineMatch` model** — add computed properties:
   - `validated_word_count: int`
   - `total_word_count: int`
   - `is_fully_validated: bool` (all words validated)

### UI

1. **Word-match grid** — add a toggle (checkbox or icon) per word.
   Validated words get a visual indicator (checkmark, background tint,
   or subtle border).

2. **Line-level indicator** — each line row shows rollup status:
   a checkmark when fully validated, or a fraction ("3/5") when
   partially validated.

3. **Paragraph-level indicator** — paragraph header shows validated
   when all its lines are fully validated, otherwise shows fraction.

4. **Page-level summary** — show "N / M words validated" in the page
   actions bar for at-a-glance progress.

## Edge Cases

- Structural edits (word merge, split, line merge/split, paragraph
  split) reset validation for affected words — the structure changed, so
  prior review no longer applies.
- Rematch GT clears validation **only for words whose GT actually
  changed**.  Implementation: before rematch, snapshot each word's
  `ground_truth_text`; after rematch, compare per-word and reset
  `is_validated` only where the value differs.  Words whose GT is
  unchanged keep their validation.
- Words added by add-word start unvalidated.
- Deleting a validated word updates the rollup counts.

## Tests

- Unit: `toggle_word_validated` sets/clears the flag and notifies.
- Unit: line rollup correctly computes partial and full validation.
- Round-trip: save a page with some validated words, reload, assert
  validation state is preserved.
- Cache round-trip: validate words, trigger auto-save-to-cache, reload
  from cache, assert validation state survives without explicit
  "Save Page".
- Structural edit: merge two words, assert merged word is unvalidated.
- Structural edit: split a validated word, assert both halves are
  unvalidated.
- Rematch GT: validate all words, rematch where only some GT changes,
  assert changed words lose validation while unchanged words keep it.
- `WordMatch` / `LineMatch` models: `is_validated` and rollup properties
  reflect underlying state.

## Done Criteria

- Users can toggle validation per-word in the word-match grid.
- Line, paragraph, and page rollups display correctly.
- Validation state persists across save/load.
- Structural edits reset validation for affected words.
- At least one round-trip test validates the behavior.
- No regression in existing tests.
