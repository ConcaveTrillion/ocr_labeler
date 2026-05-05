# How to Label a Page

This guide walks through one full labeling pass on a single page —
from opening a project to saving validated output. The labeler has a
lot of controls (~100 of them); this doc focuses on the common path
and links out for the rare ones.

If you haven't installed yet, see [Installing](installing.md). To
launch:

```sh
pd-ocr-labeler-ui /path/to/project
```

then open the URL it prints (default `http://127.0.0.1:8080/`).

## 1. Open a project

A project is just a directory of page images (`.png`, `.jpg`,
`.jpeg`). Optionally you can put a `pages.json` next to the images
mapping `filename → ground truth text`.

In the header:

- Use the **project dropdown** to pick a project under the configured
  projects root.
- Or click the 📁 icon to browse to a different folder, then **Apply**.
- Click **Load** to open the project.

`pages.json` example:

```json
{
  "001.png": "Ground truth text for first page...",
  "002.png": "Second page ground truth..."
}
```

Keys are matched case-insensitively. Variants without extension also
work.

## 2. Navigate pages

Page navigation lives at the top of the page view:

- **Prev** / **Next** to step.
- **Go To:** input — type a page number and press Enter.

The first time you visit a page the labeler runs OCR on it. A central
spinner shows while a page loads. After that it's cached.

## 3. Read the layout

The page view splits in two:

- **Left — image tabs.** The page image with selectable overlay
  variants (paragraphs / lines / words / mismatches). Toggle layers
  with the **Show Paragraphs / Show Lines / Show Words** checkboxes.
  Switch **Selection Mode** when you need to pick individual elements.
- **Right — text tabs.** Three tabs:
  - **Matches** — the main editing view: each line shown side-by-side
    with OCR words and their ground-truth alignment.
  - **Ground Truth** — the raw GT text for the page.
  - **OCR** — the raw OCR text for the page.

Most labeling work happens on the **Matches** tab.

## 4. Filter what you see

Above the matches list, a **filter toggle** cycles through:

- **Unvalidated** (default) — hides words you've already marked good,
  so you can focus on what's left.
- **Mismatched** — only words where OCR ≠ GT.
- **All** — show everything.

Use **Unvalidated** for the first sweep, **Mismatched** for cleanup.

## 5. Fix words

For each word in the matches view, you have a few tools. Pick the
lightest one that does the job.

### Inline GT edit

Click into the GT text input next to a word and type the corrected
text. Press Enter to commit. **Tab / Shift-Tab** moves between words
without leaving the keyboard.

### Bulk copy

If OCR is right and GT is wrong (or missing), use the **OCR→GT** copy
on the line; the reverse direction (**GT→OCR**) overwrites OCR with
GT. Both buttons exist at line, paragraph, and page scope on the
toolbar — pick the smallest scope that's correct.

### Word edit dialog

For anything structural, click the **edit** (pencil) icon on a word to
open the word edit dialog. From here you can:

- **Merge** with the previous or next word (`Merge Prev` /
  `Merge Next`).
- **Split** the word horizontally (**H**) or vertically (**V**).
- **Crop** the bounding box (**Crop Above / Below / Left / Right**)
  by placing the marker on the cropped image preview.
- **Refine** the bounding box automatically (`Refine` or
  `Expand + Refine`); these are *staged* — preview first, then
  **Apply** or **Apply + Refine**.
- **Fine-tune** the bbox edges with the **X− / X+ / Y− / Y+** nudge
  buttons (one click = one unit per edge).
- **Delete** the word entirely.

Use the zoom slider in the dialog to inspect details (0.5×–2×).

## 6. Edit lines, paragraphs, and pages

The toolbar has a row per scope (**Page / Paragraph / Line / Word**).
The columns are consistent: refine, copy GT↔OCR, validate, delete,
plus scope-specific actions (merge, split, group). Selection drives
scope:

- Tick the checkbox on a **word** to operate on words.
- Tick checkboxes on **lines** to operate on lines.
- Multi-select then click an action icon in that scope's row.

Common moves:

- **Merge selected lines** when OCR over-segmented a line.
- **Split paragraph after this line** when OCR under-segmented.
- **Refine all bounding boxes on this page** (page row) for a quick
  cleanup pass before per-word work.
- **Delete** rows that are header / footer / page number noise the
  layout pass missed.

Per-line buttons on the line card itself give you GT→OCR / OCR→GT /
Validate / Delete shortcuts without using the toolbar.

## 7. Tag styles and components

Some words need typographic metadata in addition to text:

- **Style dropdown + Apply Style** — italics, bold, small caps,
  blackletter, etc. The **Scope** dropdown picks whole-word vs
  partial-word.
- **Component dropdown + Apply Component** — labels structural roles
  (e.g. footnote markers). **Clear Component** removes the label.

Applied tags show as chips on the word; click the **×** on a chip to
remove a single tag.

## 8. Validate

Validation is a per-word boolean that rolls up to lines, paragraphs,
and the page. The intent: validated words are "I've reviewed this and
the GT is correct."

- Click the **check** icon on a word to toggle its validation.
- Use the **Validate** scope buttons (page / paragraph / line / word
  rows) for bulk action.
- The line card's Validate button shows a count, e.g. "3 / 5
  validated."

When the **Unvalidated** filter is active, validated words drop out of
view, so each pass shrinks the list.

## 9. Save

Two save buttons in the page actions bar:

- **Save Page** — persists just the current page (JSON + image
  artifacts) to the labeled-projects directory.
- **Save Project** — bulk-saves every page you've worked on this
  session.

After save, your labeled output lives under the OS-aware data root
(see [`DEVELOPMENT.md`](../../DEVELOPMENT.md#runtime-paths) for exact
locations).

## 10. Other useful actions

- **Reload OCR** — re-run OCR on the current page (e.g. after changing
  the OCR config in the modal).
- **Load Page** — re-load the saved labeled state for the current
  page (discards in-memory edits).
- **Rematch GT** — re-run ground-truth matching from source text,
  *replacing* any per-word GT edits. Use carefully.
- **Export** (export dialog from the page view) — produce DocTR
  training/validation export with scope selection (current page / all
  validated pages) and optional style filter.

## Tips

- **Validate as you go.** Combined with the Unvalidated filter, this
  keeps your working set small.
- **Refine bboxes at page scope first.** Saves a lot of per-word
  nudging.
- **Use OCR→GT (or GT→OCR) at line scope** when the whole line is
  one-sided right; faster than per-word.
- **Mismatches filter** for cleanup at the end of a page.
- **Tab / Shift-Tab** keep your hands on the keyboard during the long
  middle stretch of a page.
- **Save Project** before closing the tab — Save Page only persists
  the current one.

## Related docs

- Full inventory of every UI button →
  [`docs/architecture/ui-action-buttons.md`](../architecture/ui-action-buttons.md).
- Where labeled output lives on disk →
  [`DEVELOPMENT.md` — Runtime paths](../../DEVELOPMENT.md#runtime-paths).
- OCR model selection →
  [`docs/architecture/ocr-model-selection.md`](../architecture/ocr-model-selection.md).
