# pd-book-tools Model Alignment

Purpose: identify dynamic/custom attributes currently attached in `ocr_labeler` to `pd_book_tools` OCR objects, and define the upstream changes needed so these attributes exist natively in `pd-book-tools`.

Status: planned migration guide for upstream model changes.

Last validated: 2026-02-15.

## Scope

This document focuses on attributes we are **writing dynamically** onto `pd_book_tools` objects (primarily `Page`) and should instead model directly in `pd-book-tools`.

## Confirmed dynamic attributes in `ocr_labeler`

### `Page` attributes being added dynamically

Observed assignment sites include:

- `ocr_labeler/state/project_state.py`
- `ocr_labeler/state/page_state.py`
- `ocr_labeler/operations/ocr/page_operations.py`
- `ocr_labeler/operations/ocr/ocr_service.py`

Attributes:

1. `image_path`
   - Current usage: stores original image path for save/load, provenance fingerprinting, and reload behavior.
   - Current runtime values: `Path` or `str` (mixed usage).

2. `name`
   - Current usage: image filename lookup key for `ground_truth_map`, UI labeling.
   - Runtime value: `str` (e.g. `001.png`).

3. `index`
   - Current usage: local page index used by save naming and view logic.
   - Runtime value: `int`.
   - Notes: semantically duplicates `Page.page_index`.

4. `page_source`
   - Current usage: source badge/status (`RAW OCR` vs `LABELED`), refresh behavior after save/load.
   - Runtime values seen: `"ocr"`, `"filesystem"`, OCR engine values (`"doctr"`, `"tesseract"`).

5. `ocr_failed`
   - Current usage: mark fallback pages created when OCR fails.
   - Runtime value: `bool`.

6. `_ocr_labeler_live_ocr_provenance`
7. `_ocr_labeler_saved_ocr_provenance`
8. `_ocr_labeler_saved_provenance`
   - Current usage: attach provenance metadata dictionaries directly on `Page` as an optimization/cache and for save summary.
   - Runtime value: `dict[str, Any]`.

### Not part of this migration

The following are used in `ocr_labeler` but already exist (or are handled) in `pd-book-tools` and are not new model fields to add:

- `Page.add_ground_truth(...)` (already exists)
- `Page.cv2_numpy_page_image` (already exists)
- `Word.ground_truth_text` (already exists)
- `Block.unmatched_ground_truth_words` (already exists)

## Upstream model changes to implement in `pd-book-tools`

Target file: `pd_book_tools/ocr/page.py`

### 1) Add first-class metadata fields on `Page`

Add constructor parameters + instance fields:

- `image_path: pathlib.Path | str | None = None`
- `name: str | None = None`
- `source: str = "ocr"`
- `ocr_failed: bool = False`
- `provenance_live_ocr: dict[str, Any] | None = None`
- `provenance_saved_ocr: dict[str, Any] | None = None`
- `provenance_saved: dict[str, Any] | None = None`

Recommended normalization behavior:

- Keep `index` as a compatibility property aliasing `page_index`.
  - getter: returns `page_index`
  - setter: writes `page_index`
- Keep `page_source` as a compatibility property aliasing `source`.

Rationale:

- Removes repeated `# type: ignore[attr-defined]` in app code.
- Makes model intent explicit and discoverable.
- Preserves compatibility with existing `ocr_labeler` call sites during migration.

### 2) Include new metadata in serialization

Update `Page.to_dict()` and `Page.from_dict()` to round-trip these fields.

Recommended keys:

- `image_path` (stringified path)
- `name`
- `source`
- `ocr_failed`
- `provenance_live_ocr`
- `provenance_saved_ocr`
- `provenance_saved`

Compatibility behavior:

- When loading older data without these keys, keep defaults.
- When both `source` and legacy `page_source` are present, `source` wins.

### 3) Prefer explicit metadata API over direct external setattr

Optional but recommended convenience API in `Page`:

- `set_source(source: str) -> None`
- `mark_ocr_failed(failed: bool = True) -> None`
- `set_image_path(path: pathlib.Path | str | None) -> None`

This keeps normalization logic inside `Page` and reduces app-side conditional checks.

## Copilot implementation checklist (for upstream PR)

1. Modify `pd_book_tools/ocr/page.py`:
   - Add new fields/constructor args.
   - Add `index` and `page_source` compatibility properties.
   - Extend `to_dict`/`from_dict`.

2. Add/adjust tests in `pd-book-tools`:
   - `Page` metadata defaults.
   - `index` <-> `page_index` alias behavior.
   - `page_source` <-> `source` alias behavior.
   - Serialization round-trip with/without metadata keys.

3. After upstream release, simplify `ocr_labeler`:
   - Remove `type: ignore[attr-defined]` for these fields.
   - Replace dynamic attribute checks (`hasattr(page, "page_source")`, etc.) with direct usage.
   - Rename private ad-hoc provenance attribute constants to direct typed fields.

## Suggested typed shape (reference)

Use this as a target shape in `pd-book-tools` (exact style can follow upstream conventions):

```python
@property
def index(self) -> int:
    return self.page_index

@index.setter
def index(self, value: int) -> None:
    self.page_index = int(value)

@property
def page_source(self) -> str:
    return self.source

@page_source.setter
def page_source(self, value: str) -> None:
    self.source = value
```

## Migration notes for `ocr_labeler`

Once upstream fields are available, replace dynamic assignment blocks such as:

- `page.image_path = ...`
- `page.name = ...`
- `page.index = ...`
- `page.page_source = ...`
- `setattr(page, "_ocr_labeler_saved_provenance", ...)`

with direct typed assignments and remove local fallback caches that only exist to compensate for missing upstream model fields.
