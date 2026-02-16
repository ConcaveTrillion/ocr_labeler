from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    from pd_book_tools.ocr.provenance import OCRModelProvenance, OCRProvenance
except ImportError:

    @dataclass(frozen=True)
    class OCRModelProvenance:
        name: str
        version: str | None = None
        weights_id: str | None = None

        def to_dict(self) -> dict[str, Any]:
            result: dict[str, Any] = {"name": self.name}
            if self.version:
                result["version"] = self.version
            if self.weights_id:
                result["weights_id"] = self.weights_id
            return result

        @classmethod
        def from_dict(cls, data: dict[str, Any]) -> "OCRModelProvenance":
            return cls(
                name=str(data.get("name", "unknown")),
                version=(
                    str(data["version"]) if data.get("version") is not None else None
                ),
                weights_id=(
                    str(data["weights_id"])
                    if data.get("weights_id") is not None
                    else None
                ),
            )

    @dataclass(frozen=True)
    class OCRProvenance:
        engine: str = "unknown"
        engine_version: str | None = None
        models: list[OCRModelProvenance] = field(default_factory=list)
        config_fingerprint: str | None = None

        def to_dict(self) -> dict[str, Any]:
            result: dict[str, Any] = {
                "engine": self.engine,
                "models": [model.to_dict() for model in self.models],
            }
            if self.engine_version:
                result["engine_version"] = self.engine_version
            if self.config_fingerprint:
                result["config_fingerprint"] = self.config_fingerprint
            return result

        @classmethod
        def from_dict(cls, data: dict[str, Any]) -> "OCRProvenance":
            raw_models = data.get("models", [])
            models: list[OCRModelProvenance] = []
            if isinstance(raw_models, list):
                for model in raw_models:
                    if isinstance(model, dict):
                        models.append(OCRModelProvenance.from_dict(model))
                    elif isinstance(model, str) and model:
                        models.append(OCRModelProvenance(name=model))

            return cls(
                engine=str(data.get("engine", "unknown")),
                engine_version=(
                    str(data["engine_version"])
                    if data.get("engine_version") is not None
                    else None
                ),
                models=models,
                config_fingerprint=(
                    str(data["config_fingerprint"])
                    if data.get("config_fingerprint") is not None
                    else None
                ),
            )


USER_PAGE_SCHEMA_NAME = "ocr_labeler.user_page"
USER_PAGE_SCHEMA_VERSION = "2.0"

USER_PAGE_SOURCE_LANE_LABELED = "labeled"
USER_PAGE_SAVED_BY_SAVE_PAGE = "Save Page"
UNKNOWN_METADATA_VALUE = "unknown"


@dataclass(frozen=True)
class UserPageSchema:
    name: str = USER_PAGE_SCHEMA_NAME
    version: str = USER_PAGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "version": self.version}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPageSchema":
        return cls(
            name=str(data.get("name", USER_PAGE_SCHEMA_NAME)),
            version=str(data.get("version", USER_PAGE_SCHEMA_VERSION)),
        )


@dataclass(frozen=True)
class ProvenanceApp:
    name: str = "ocr_labeler"
    version: str = UNKNOWN_METADATA_VALUE
    git_commit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "version": self.version,
        }
        if self.git_commit:
            result["git_commit"] = self.git_commit
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProvenanceApp":
        return cls(
            name=str(data.get("name", "ocr_labeler")),
            version=str(data.get("version", UNKNOWN_METADATA_VALUE)),
            git_commit=(
                str(data["git_commit"]) if data.get("git_commit") is not None else None
            ),
        )


@dataclass(frozen=True)
class ProvenanceToolchain:
    python: str = UNKNOWN_METADATA_VALUE
    pd_book_tools: str = UNKNOWN_METADATA_VALUE
    opencv_python: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "python": self.python,
            "pd_book_tools": self.pd_book_tools,
        }
        if self.opencv_python:
            result["opencv_python"] = self.opencv_python
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProvenanceToolchain":
        return cls(
            python=str(data.get("python", UNKNOWN_METADATA_VALUE)),
            pd_book_tools=str(data.get("pd_book_tools", UNKNOWN_METADATA_VALUE)),
            opencv_python=(
                str(data["opencv_python"])
                if data.get("opencv_python") is not None
                else None
            ),
        )


ProvenanceOCRModel = OCRModelProvenance
ProvenanceOCR = OCRProvenance


@dataclass(frozen=True)
class UserPageProvenance:
    saved_at: str
    saved_by: str = USER_PAGE_SAVED_BY_SAVE_PAGE
    source_lane: str = USER_PAGE_SOURCE_LANE_LABELED
    app: ProvenanceApp = field(default_factory=ProvenanceApp)
    toolchain: ProvenanceToolchain = field(default_factory=ProvenanceToolchain)
    ocr: ProvenanceOCR = field(default_factory=ProvenanceOCR)

    def to_dict(self) -> dict[str, Any]:
        return {
            "saved_at": self.saved_at,
            "saved_by": self.saved_by,
            "source_lane": self.source_lane,
            "app": self.app.to_dict(),
            "toolchain": self.toolchain.to_dict(),
            "ocr": self.ocr.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPageProvenance":
        return cls(
            saved_at=str(data.get("saved_at", "")),
            saved_by=str(data.get("saved_by", USER_PAGE_SAVED_BY_SAVE_PAGE)),
            source_lane=str(data.get("source_lane", USER_PAGE_SOURCE_LANE_LABELED)),
            app=ProvenanceApp.from_dict(data.get("app", {})),
            toolchain=ProvenanceToolchain.from_dict(data.get("toolchain", {})),
            ocr=ProvenanceOCR.from_dict(data.get("ocr", {})),
        )


@dataclass(frozen=True)
class SourceImageFingerprint:
    size: int | None = None
    mtime_ns: int | None = None
    sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.size is not None:
            result["size"] = self.size
        if self.mtime_ns is not None:
            result["mtime_ns"] = self.mtime_ns
        if self.sha256 is not None:
            result["sha256"] = self.sha256
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceImageFingerprint":
        return cls(
            size=int(data["size"]) if data.get("size") is not None else None,
            mtime_ns=(
                int(data["mtime_ns"]) if data.get("mtime_ns") is not None else None
            ),
            sha256=(str(data["sha256"]) if data.get("sha256") is not None else None),
        )


@dataclass(frozen=True)
class UserPageSource:
    project_id: str
    page_index: int
    page_number: int
    image_path: str
    project_root: str | None = None
    image_fingerprint: SourceImageFingerprint | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "project_id": self.project_id,
            "page_index": self.page_index,
            "page_number": self.page_number,
            "image_path": self.image_path,
        }
        if self.project_root:
            result["project_root"] = self.project_root
        if self.image_fingerprint:
            result["image_fingerprint"] = self.image_fingerprint.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPageSource":
        fingerprint_data = data.get("image_fingerprint")
        image_fingerprint = (
            SourceImageFingerprint.from_dict(fingerprint_data)
            if isinstance(fingerprint_data, dict)
            else None
        )
        return cls(
            project_id=str(data.get("project_id", "")),
            page_index=int(data.get("page_index", 0)),
            page_number=int(data.get("page_number", 0)),
            image_path=str(data.get("image_path", "")),
            project_root=(
                str(data["project_root"])
                if data.get("project_root") is not None
                else None
            ),
            image_fingerprint=image_fingerprint,
        )


@dataclass(frozen=True)
class UserPagePayload:
    page: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"page": self.page}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPagePayload":
        page_data = data.get("page")
        if not isinstance(page_data, dict):
            page_data = {}
        return cls(page=page_data)


@dataclass(frozen=True)
class UserPageEnvelope:
    schema: UserPageSchema
    provenance: UserPageProvenance
    source: UserPageSource
    payload: UserPagePayload

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema.to_dict(),
            "provenance": self.provenance.to_dict(),
            "source": self.source.to_dict(),
            "payload": self.payload.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPageEnvelope":
        return cls(
            schema=UserPageSchema.from_dict(data.get("schema", {})),
            provenance=UserPageProvenance.from_dict(data.get("provenance", {})),
            source=UserPageSource.from_dict(data.get("source", {})),
            payload=UserPagePayload.from_dict(data.get("payload", {})),
        )


def is_user_page_envelope(data: dict[str, Any]) -> bool:
    schema = data.get("schema")
    if not isinstance(schema, dict):
        return False
    return str(schema.get("name")) == USER_PAGE_SCHEMA_NAME
