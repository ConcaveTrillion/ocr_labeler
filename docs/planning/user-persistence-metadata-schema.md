# User Persistence Metadata Schema Plan

## Purpose

Define an explicit storage format for **user-authoritative saved page data** (`Save Page`) that captures provenance and compatibility metadata, including:

- this app (`ocr_labeler`) version/build information
- supporting library/toolchain versions (including `pd-book-tools`)
- OCR engine + model configuration used to generate baseline OCR

This document applies to the **user edits lane** (authoritative labeled outputs), not the transient/optimization cache lane.

## Why This Is Needed

User-labeled outputs should remain interpretable and auditable over time. Without embedded provenance, it is difficult to:

- explain differences after upgrades
- detect when saved data came from incompatible OCR/model pipelines
- migrate old saved outputs safely

## Scope

### In Scope

- Extend saved user page JSON format with metadata envelope
- Version the persistence schema itself
- Persist enough OCR/model/toolchain information for reproducibility and migration decisions
- Define backward-compatible loading and migration behavior

### Out of Scope

- Full dataset export format redesign
- Replacing existing page/word structures from `pd-book-tools`
- Distributed synchronization concerns

## Canonical Data Structure (Proposed)

Saved user page JSON should include:

```json
{
  "schema": {
    "name": "ocr_labeler.user_page",
    "version": "2.0"
  },
  "provenance": {
    "saved_at": "2026-02-15T12:34:56Z",
    "saved_by": "Save Page",
    "source_lane": "labeled",
    "app": {
      "name": "ocr_labeler",
      "version": "x.y.z",
      "git_commit": "optional"
    },
    "toolchain": {
      "python": "3.13.x",
      "pd_book_tools": "x.y.z",
      "opencv_python": "optional"
    },
    "ocr": {
      "engine": "doctr|tesseract|other",
      "engine_version": "optional",
      "models": [
        {
          "name": "det_model",
          "version": "optional",
          "weights_id": "optional"
        },
        {
          "name": "rec_model",
          "version": "optional",
          "weights_id": "optional"
        }
      ],
      "config_fingerprint": "optional-stable-hash"
    }
  },
  "source": {
    "project_id": "project-name",
    "project_root": "optional",
    "page_index": 0,
    "page_number": 1,
    "image_path": "relative/path.png",
    "image_fingerprint": {
      "size": 123456,
      "mtime_ns": 1234567890123,
      "sha256": "optional"
    }
  },
  "payload": {
    "page": {}
  }
}
```

Notes:

- `payload.page` contains the existing `Page.to_dict()` output.
- Optional fields are allowed where runtime introspection is unavailable.
- `schema.version` controls migration behavior.

## Required Metadata (MVP)

Required to write:

- `schema.name`, `schema.version`
- `provenance.saved_at`, `provenance.saved_by`, `provenance.app.version`
- `provenance.toolchain.pd_book_tools` (or `"unknown"` if unavailable)
- `provenance.ocr.engine`
- `source.page_index`, `source.page_number`, `source.image_path`
- `payload.page`

Required to read:

- tolerate missing fields for legacy files
- default unknown metadata safely
- never fail page load solely because optional provenance is absent

## Versioning & Compatibility

### Schema Semantics

- `1.x`: legacy flat format (`source_lib`, `source_path`, `pages`)
- `2.0`: metadata envelope format above

### Loader Rules

1. If `schema.version` exists and supported, parse envelope.
2. If schema missing, treat as legacy and map to internal normalized structure.
3. Preserve legacy files on disk; migrate in-memory first.
4. Optional future: write-back migration when user explicitly saves.

## Storage Layout

User-authoritative lane remains separate from cache lane:

- User-labeled output path: existing labeled output directory/files.
- Cache output path: separate cache directory/namespace.

The same page may exist in both lanes, but lane precedence for user operations should favor labeled output.

## Read/Write Behavior

### Write (`Save Page`)

- Always write user-authoritative format (`schema.version = 2.0`).
- Capture runtime version metadata best-effort.
- Use atomic writes to avoid partial file corruption.

### Read (`Load Page`)

- Accept both legacy and `2.0` envelope formats.
- Expose parsed provenance metadata for UI display/debugging.
- Keep behavior stable even when metadata fields are unknown.

## UI/UX Notes

- For `LABELED` page source, tooltip can display provenance summary:
  - app version
  - `pd-book-tools` version
  - OCR engine/model fingerprint
  - saved timestamp

This is informational and should not block loading.

## Migration Strategy

Phase 1:

- Implement dual-reader (legacy + v2).
- Keep writer unchanged behind feature flag if needed.

Phase 2:

- Switch `Save Page` writer to v2 by default.
- Add tests for backward compatibility and provenance presence.

Phase 3:

- Optional explicit migration command for historical labeled files.

## Testing Plan

- Unit tests for v2 serialization/deserialization.
- Unit tests for legacy file compatibility.
- Unit tests for missing/partial provenance fields.
- Integration test: save user edits -> reload -> verify payload + provenance retained.

## Risks & Mitigations

- **Risk:** incomplete runtime version detection.
  - **Mitigation:** store `"unknown"` with consistent keys; avoid write failure.
- **Risk:** accidental schema drift.
  - **Mitigation:** central schema constants + validation helpers.
- **Risk:** conflating cache and labeled lanes.
  - **Mitigation:** enforce separate directories and explicit lane labels in code.

## Execution Checklist

- [ ] Add schema constants and metadata model for user persistence envelope.
- [ ] Implement dual-reader for legacy + v2 formats.
- [ ] Update `Save Page` writer to emit v2 envelope.
- [ ] Capture app/toolchain/OCR provenance at save-time.
- [x] Surface labeled provenance metadata in UI tooltip.
- [ ] Add regression tests for compatibility and metadata retention.
