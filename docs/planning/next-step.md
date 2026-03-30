# Next Step: Preserve Per-Word GT Edits Across Save/Load

Goal: ensure that manual per-word ground truth edits survive page save/load
round-trips and are not silently overwritten by bulk GT re-injection.

## Problem

Per-word GT fields (`ground_truth_text`, `ground_truth_match_keys`) are
correctly serialized by `Page.to_dict()` and restored by `Page.from_dict()`.
However, when a saved page is loaded back, `PageState.load_page_from_file()`
calls `page.add_ground_truth(gt_text)` which internally runs
`remove_ground_truth()` then re-runs the difflib-based matching algorithm.
This **wipes any manual per-word GT edits** the user made before saving.

Affected code path:

```text
PageState.load_page_from_file()          [page_state.py ~line 599]
  -> Page.from_dict(payload)             # restores saved word GT (correct)
  -> page.add_ground_truth(gt_text)      # wipes + re-matches (destructive)
```

## Desired Behavior

- If a page was previously saved with per-word GT edits, those edits are
  preserved on reload — the bulk re-match step is skipped.
- If a page has no saved per-word GT (first-time load, cache-only), the
  existing bulk match behavior continues unchanged.
- A user can explicitly request GT re-match to reset edits (e.g. after
  `pages.json` changes).

## Implementation Sketch

1. **Detect saved GT on load** — after `Page.from_dict()`, check whether
   the deserialized words already carry `ground_truth_text` values.  If
   they do, skip the `add_ground_truth()` call.

2. **Persist a "gt_edited" flag** — add a boolean to the
   `UserPagePayload` (or envelope metadata) that records whether any
   word-level GT was manually edited.  On load, consult this flag to
   decide whether to re-match.  Bump schema version if needed.

3. **Explicit re-match action** — expose a UI action (button or menu
   item) that calls `remove_ground_truth()` + `add_ground_truth()` so the
   user can intentionally refresh GT matching when the source text changes.

4. **Per-line validation state (stretch)** — add an `is_validated: bool`
   field to the line/block model so users can mark individual lines as
   reviewed.  Persist it in the payload alongside `word_attributes`.

## Edge Cases

- Page loaded from cache vs. from explicit save — cache pages may not
  have user-edited GT; treat them the same as fresh pages.
- `pages.json` updated after save — the explicit re-match action covers
  this.  Consider surfacing a hint if `pages.json` mtime is newer than
  the saved page.

## Tests

- Round-trip test: save a page with edited per-word GT, reload, assert
  edits survive.
- Round-trip test: save a page without GT edits, reload with GT text
  available, assert bulk match runs normally.
- Explicit re-match test: trigger re-match on a page with saved GT
  edits, assert GT is refreshed from `pages.json`.

## Done Criteria

- Manual per-word GT edits persist across save/load without being
  overwritten.
- Bulk GT re-match still works for pages without prior GT edits.
- At least one round-trip test validates the behavior.
- No regression in existing tests.
