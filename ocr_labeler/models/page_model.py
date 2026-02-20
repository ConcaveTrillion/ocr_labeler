from __future__ import annotations

from pathlib import Path
from typing import Any

from pd_book_tools.ocr.page import Page


class PageModel:
    """Application-owned wrapper around OCR Page plus UI/persistence metadata."""

    def __init__(
        self,
        page: Page,
        page_source: str = "ocr",
        image_path: str | None = None,
        name: str | None = None,
        index: int | None = None,
        ocr_failed: bool = False,
        ocr_provenance: Any | None = None,
        saved_provenance: dict[str, Any] | None = None,
    ) -> None:
        self.page = page
        self.page_source = page_source
        self.ocr_failed = ocr_failed
        self.saved_provenance = saved_provenance
        self._image_path: str | None = None
        self._name: str | None = None
        self._index: int | None = None
        self._ocr_provenance: Any | None = None

        if image_path is not None:
            self.image_path = image_path
        else:
            self._image_path = self._normalize_image_path(
                getattr(self.page, "image_path", None)
            )

        if name is not None:
            self.name = name
        else:
            page_name = getattr(self.page, "name", None)
            self._name = str(page_name) if page_name is not None else None

        if index is not None:
            self.index = index
        else:
            raw_index = getattr(self.page, "index", None)
            self._index = int(raw_index) if isinstance(raw_index, int) else None

        if ocr_provenance is not None:
            self.ocr_provenance = ocr_provenance
        else:
            self._ocr_provenance = getattr(self.page, "ocr_provenance", None)

    @staticmethod
    def _normalize_image_path(value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    @property
    def image_path(self) -> str | None:
        page_image_path = getattr(self.page, "image_path", None)
        normalized = self._normalize_image_path(page_image_path)
        if normalized is not None:
            return normalized
        return self._image_path

    @image_path.setter
    def image_path(self, value: str | None) -> None:
        normalized = self._normalize_image_path(value)
        self._image_path = normalized
        try:
            self.page.image_path = normalized  # type: ignore[attr-defined]
        except Exception:
            pass

    @property
    def name(self) -> str | None:
        page_name = getattr(self.page, "name", None)
        if page_name is not None:
            return str(page_name)
        return self._name

    @name.setter
    def name(self, value: str | None) -> None:
        normalized = str(value) if value is not None else None
        self._name = normalized
        try:
            self.page.name = normalized  # type: ignore[attr-defined]
        except Exception:
            pass

    @property
    def index(self) -> int | None:
        page_index = getattr(self.page, "index", None)
        if isinstance(page_index, int):
            return page_index
        return self._index

    @index.setter
    def index(self, value: int | None) -> None:
        normalized = int(value) if isinstance(value, int) else None
        self._index = normalized
        try:
            self.page.index = normalized  # type: ignore[attr-defined]
        except Exception:
            pass

    @property
    def ocr_provenance(self) -> Any | None:
        page_provenance = getattr(self.page, "ocr_provenance", None)
        if page_provenance is not None:
            return page_provenance
        return self._ocr_provenance

    @ocr_provenance.setter
    def ocr_provenance(self, value: Any | None) -> None:
        self._ocr_provenance = value
        try:
            self.page.ocr_provenance = value  # type: ignore[attr-defined]
        except Exception:
            pass

    def to_dict(self) -> dict[str, Any]:
        return self.page.to_dict()

    def add_ground_truth(self, text: str) -> None:
        self.page.add_ground_truth(text)

    def get_image_path(self) -> Path | None:
        if not self.image_path:
            return None
        return Path(self.image_path)

    def __getattr__(self, attr_name: str) -> Any:
        return getattr(self.page, attr_name)
