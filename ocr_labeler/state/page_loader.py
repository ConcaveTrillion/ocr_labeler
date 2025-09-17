# from __future__ import annotations
import logging
from pathlib import Path

from pd_book_tools.ocr.page import Page

logger = logging.getLogger(__name__)


def build_initial_page_parser(docTR_predictor=None):
    """Return an initial page parser that performs OCR via DocTR when invoked.

    This creates a parser for the initial OCR processing of pages from images.
    This is distinct from loading/saving work done on already processed pages.

    Separated for easier testing & potential alternative implementations (e.g.,
    different OCR engines or caching strategies).
    """

    def _get_predictor():
        if docTR_predictor is None:
            from pd_book_tools.ocr.doctr_support import get_default_doctr_predictor

            predictor = get_default_doctr_predictor()
        return predictor

    def _parse_page(
        path: Path,
        index: int,
        ground_truth_string: str,
        rerun_ocr_and_match: bool = False,
    ) -> Page:
        # TODO: check save location to see if this page has already been processed, if so, deserialize that if rerun_ocr_and_match is False

        from pd_book_tools.ocr.document import Document

        predictor = _get_predictor()
        doc = Document.from_image_ocr_via_doctr(
            path,
            source_identifier=path.name,
            predictor=predictor,
        )
        page_obj: Page = doc.pages[0]

        if ground_truth_string:
            page_obj.add_ground_truth(ground_truth_string)

        return page_obj

    return _parse_page
