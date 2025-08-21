from __future__ import annotations
from pathlib import Path
from pd_book_tools.ocr.page import Page  # type: ignore
import logging

logger = logging.getLogger(__name__)


def build_page_loader():
    """Return a lazy page loader that performs OCR via DocTR when invoked.

    Separated for easier testing & potential alternative implementations (e.g.,
    different OCR engines or caching strategies).
    """
    def _load_page(path: Path, index: int) -> Page:  # pragma: no cover - runtime side-effect
        from pd_book_tools.ocr.document import Document  # type: ignore
        from pd_book_tools.ocr.doctr_support import get_default_doctr_predictor  # type: ignore
        predictor = get_default_doctr_predictor()
        doc = Document.from_image_ocr_via_doctr(
            path,
            source_identifier=path.name,
            predictor=predictor,
        )
        page_obj: Page = doc.pages[0]
        return page_obj

    return _load_page
