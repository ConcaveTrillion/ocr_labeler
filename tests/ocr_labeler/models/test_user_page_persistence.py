from __future__ import annotations

from ocr_labeler.models import (
    UNKNOWN_METADATA_VALUE,
    USER_PAGE_SAVED_BY_SAVE_PAGE,
    USER_PAGE_SCHEMA_NAME,
    USER_PAGE_SCHEMA_VERSION,
    USER_PAGE_SOURCE_LANE_LABELED,
    ProvenanceApp,
    ProvenanceOCR,
    ProvenanceOCRModel,
    ProvenanceToolchain,
    SourceImageFingerprint,
    UserPageEnvelope,
    UserPagePayload,
    UserPageProvenance,
    UserPageSchema,
    UserPageSource,
    is_user_page_envelope,
)


def test_user_page_schema_defaults() -> None:
    schema = UserPageSchema()
    assert schema.name == USER_PAGE_SCHEMA_NAME
    assert schema.version == USER_PAGE_SCHEMA_VERSION


def test_envelope_round_trip_serialization() -> None:
    envelope = UserPageEnvelope(
        schema=UserPageSchema(),
        provenance=UserPageProvenance(
            saved_at="2026-02-15T12:34:56Z",
            app=ProvenanceApp(version="0.1.0"),
            toolchain=ProvenanceToolchain(python="3.13.1", pd_book_tools="0.1.0"),
            ocr=ProvenanceOCR(
                engine="doctr",
                engine_version="0.11.0",
                models=[
                    ProvenanceOCRModel(name="det_model", version="v1"),
                    ProvenanceOCRModel(name="rec_model", weights_id="weights-123"),
                ],
                config_fingerprint="abc123",
            ),
        ),
        source=UserPageSource(
            project_id="book-1",
            page_index=0,
            page_number=1,
            image_path="images/001.png",
            image_fingerprint=SourceImageFingerprint(size=1024, mtime_ns=42),
        ),
        payload=UserPagePayload(
            page={
                "type": "Page",
                "items": [],
                "page_index": 0,
            }
        ),
    )

    serialized = envelope.to_dict()
    restored = UserPageEnvelope.from_dict(serialized)

    assert restored.schema.name == USER_PAGE_SCHEMA_NAME
    assert restored.schema.version == USER_PAGE_SCHEMA_VERSION
    assert restored.provenance.saved_by == USER_PAGE_SAVED_BY_SAVE_PAGE
    assert restored.provenance.source_lane == USER_PAGE_SOURCE_LANE_LABELED
    assert restored.provenance.ocr.engine == "doctr"
    assert len(restored.provenance.ocr.models) == 2
    assert restored.source.project_id == "book-1"
    assert restored.source.image_fingerprint is not None
    assert restored.source.image_fingerprint.size == 1024
    assert restored.payload.page["type"] == "Page"


def test_from_dict_uses_safe_defaults_for_partial_payload() -> None:
    envelope = UserPageEnvelope.from_dict(
        {
            "schema": {"name": USER_PAGE_SCHEMA_NAME},
            "provenance": {"saved_at": "2026-02-15T00:00:00Z"},
            "source": {},
            "payload": {},
        }
    )

    assert envelope.schema.version == USER_PAGE_SCHEMA_VERSION
    assert envelope.provenance.app.version == UNKNOWN_METADATA_VALUE
    assert envelope.provenance.toolchain.pd_book_tools == UNKNOWN_METADATA_VALUE
    assert envelope.payload.page == {}


def test_is_user_page_envelope() -> None:
    assert is_user_page_envelope({"schema": {"name": USER_PAGE_SCHEMA_NAME}}) is True
    assert is_user_page_envelope({"schema": {"name": "other"}}) is False
    assert is_user_page_envelope({}) is False
