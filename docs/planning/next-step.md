# Next Step: Ground Truth PGDP Preprocessing

Goal: pass raw PGDP ground truth text through the `PGDPResults` preprocessor
before matching it against OCR output, so that GT text is in an OCR-comparable
format.

## Problem

Ground truth text loaded from `pages.json` is raw PGDP proofreader output. It
contains PGDP-specific markup (diacritic codes, footnote bracket notation,
ASCII dash conventions, straight quotes, proofer notes, etc.) that does not
match what an OCR engine produces. Without preprocessing, the GT-to-OCR word
matching produces excessive false mismatches.

## Available Preprocessor

`pd-book-tools` already provides a full preprocessing pipeline:

- **`PGDPResults`** (`pd_book_tools.pgdp.pgdp_results`)
  - Normalizes line endings
  - Removes proofer notes (`[*...*]`)
  - Removes `[Blank Page]` markers
  - Converts PGDP diacritic markup to Unicode (macrons, umlauts, accents, etc.)
  - Converts footnote markers (e.g. `[12]` -> space-separated number `12`)
  - Handles hyphenation continuations (`-*`)
  - Converts ASCII dashes to em/two-em dash Unicode characters
  - Strips page continuation asterisks
  - Converts straight quotes to curly quotes

- **`PGDPExport`** (same module) -- loads a multi-page PGDP JSON export and
  creates a `PGDPResults` per page automatically.

## Integration Path

The existing `pd-book-tools` integration point is:

```text
PGDPResults(filename, raw_text)
  -> pgdp_results.processed_page_text
    -> page.add_ground_truth(processed_text)
      -> update_page_with_ground_truth_text() in ground_truth_matching.py
```

## Implementation Checklist

1. **Locate GT ingestion in `ocr_labeler`**
   - Find where raw `pages.json` text is read and passed to
     `page.add_ground_truth()`.
   - Confirm the text is currently passed without preprocessing.

2. **Add PGDP preprocessing step**
   - Import `PGDPResults` from `pd_book_tools.pgdp.pgdp_results`.
   - Before calling `add_ground_truth()`, run the raw text through
     `PGDPResults(image_filename, raw_text)`.
   - Pass `pgdp_results.processed_page_text` to `add_ground_truth()`.

3. **Consider `PGDPExport` for bulk loading**
   - If the project loads GT from a single JSON file mapping filenames to text,
     `PGDPExport.from_json_file(path)` may be a cleaner integration point
     (preprocesses all pages at load time).

4. **Handle edge cases**
   - GT text that is already preprocessed (non-PGDP sources) -- consider a
     flag or heuristic to skip preprocessing when not needed.
   - Empty or missing GT text -- ensure no crash on empty input.

5. **Validate matching improvement**
   - Compare mismatch counts before/after preprocessing on a sample project.
   - Verify curly quotes, diacritics, and dashes now match OCR output.

6. **Tests**
   - Unit test confirming GT text passes through `PGDPResults` before matching.
   - Integration test with sample PGDP markup verifying reduced mismatches.

## Done Criteria

- Raw PGDP text from `pages.json` is preprocessed via `PGDPResults` before
  GT matching.
- PGDP-specific markup (diacritics, footnotes, dashes, quotes, proofer notes)
  no longer causes false mismatches in the word match grid.
- Existing tests pass; no regression in non-PGDP GT workflows.
