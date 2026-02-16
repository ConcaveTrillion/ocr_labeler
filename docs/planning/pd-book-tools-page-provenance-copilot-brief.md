# Copilot Brief: Move OCR Provenance to `pd-book-tools` `Page` Model

## Context

`ocr_labeler` currently attaches OCR provenance metadata to `Page` instances using dynamic attributes (for example, `_ocr_labeler_live_ocr_provenance`).

The goal is to move OCR provenance ownership into `pd-book-tools` at the `Page` object level so provenance travels with `Page` through normal serialization (`to_dict` / `from_dict`) and copy flows.

## Objective

Implement native `Page`-level OCR provenance support in `pd-book-tools` with backward compatibility.

Key outcome:

- `Page` has a first-class field for OCR provenance metadata.
- `Page.to_dict()` persists it.
- `Page.from_dict()` restores it.
- Existing JSON without provenance still loads.

## Repository and Primary Files

Work in sibling repo: `../pd-book-tools`

Primary targets:

- `pd_book_tools/ocr/page.py`
- `pd_book_tools/ocr/document.py`
- `tests/ocr/test_page.py`
- Optional additional tests in `tests/ocr/test_document.py` if needed

## Implementation Requirements

1. **Add a typed OCR provenance field on `Page`**
   - Add an optional field on `Page` for OCR provenance metadata.
   - Keep it JSON-serializable and flexible enough for different OCR engines.
   - Recommended shape: `ocr_provenance: Optional[Dict[str, Any]] = None`.

2. **Extend `Page.__init__`**
   - Accept `ocr_provenance` as an optional parameter.
   - Store defensively (copy dictionary) to avoid accidental shared mutation.

3. **Update serialization/deserialization**
   - In `Page.to_dict()`, include `ocr_provenance`.
   - In `Page.from_dict()`, restore `ocr_provenance` when present.
   - Backward compatibility: missing `ocr_provenance` must not fail and should default to `None`.

4. **Propagate provenance during OCR construction**
   - In `Document.from_doctr_output(...)` and/or `Document.from_image_ocr_via_doctr(...)`, initialize `Page.ocr_provenance` with best-effort metadata available at creation time.
   - Keep this minimal and deterministic; avoid expensive runtime introspection.
   - Suggested minimum keys:
     - `engine` (e.g., `"doctr"`)
     - `source_lib` (if available)
     - `models` (empty list if unknown)
     - `engine_version` (`"unknown"` if unavailable)

5. **Preserve behavior of existing APIs**
   - Do not break current `Page` constructor call sites.
   - Keep existing output fields untouched except for additive `ocr_provenance`.
   - Avoid introducing app-specific naming (`ocr_labeler` should not appear in `pd-book-tools` core models).

## Test Requirements

Add/adjust tests to cover:

1. `Page.to_dict()` includes `ocr_provenance` when set.
2. `Page.from_dict()` restores `ocr_provenance`.
3. `Page.from_dict()` handles legacy dicts without `ocr_provenance`.
4. `Page.copy()` preserves `ocr_provenance` (via to/from dict flow).
5. (If implemented in `Document`) OCR-created pages contain non-`None` baseline `ocr_provenance`.

Prefer adding to existing test file:

- `tests/ocr/test_page.py`

And only add to `tests/ocr/test_document.py` for OCR-construction assertions.

## Non-Goals

- Do not redesign full persistence envelope/schema in `pd-book-tools`.
- Do not add app/toolchain provenance fields specific to `ocr_labeler`.
- Do not require provenance for successful load.

## Suggested Copilot Prompt (copy/paste)

Implement OCR provenance at the `Page` model level in this repository.

Requirements:

1. Update `pd_book_tools/ocr/page.py` to add an optional `ocr_provenance` field to `Page`.
2. Update `Page.__init__`, `Page.to_dict()`, and `Page.from_dict()` so provenance round-trips.
3. Ensure backward compatibility with existing JSON payloads that do not have provenance.
4. Update OCR construction in `pd_book_tools/ocr/document.py` so OCR-created pages get baseline provenance metadata (`engine`, `source_lib`, `models`, `engine_version`).
5. Add tests in `tests/ocr/test_page.py` (and `tests/ocr/test_document.py` only if needed) for round-trip, legacy compatibility, and copy behavior.

Constraints:

- Keep changes additive and minimal.
- Avoid `ocr_labeler`-specific fields or naming.
- Do not break existing constructor call sites.

Validation:

- Run targeted tests first: `pytest tests/ocr/test_page.py`.
- Then run broader OCR tests if needed.

## Acceptance Criteria

- `Page` objects can carry OCR provenance natively.
- Provenance survives `to_dict()` / `from_dict()` / `copy()`.
- Legacy serialized pages remain loadable.
- Tests pass for new coverage.
