"""Text operations for managing OCR and ground truth text retrieval and caching."""

import logging
from typing import Optional, Tuple

from pd_book_tools.ocr.page import Page

logger = logging.getLogger(__name__)


class TextOperations:
    """Operations for handling text retrieval and caching.

    Provides methods for extracting OCR and ground truth text from pages,
    with caching support for performance optimization.
    """

    @staticmethod
    def get_page_texts(
        page: Optional[Page], ground_truth_map: Optional[dict] = None
    ) -> Tuple[str, str]:
        """Get OCR and ground truth text for a page.

        Args:
            page: The page object to extract text from
            ground_truth_map: Optional mapping of page names to ground truth text

        Returns:
            Tuple of (ocr_text, ground_truth_text) where each is a string
        """
        if not page:
            return "", ""

        # Get OCR text from page
        ocr_text = getattr(page, "text", "") or ""
        if isinstance(ocr_text, str):
            ocr_text = ocr_text if ocr_text.strip() else ""
        else:
            ocr_text = ""

        # Get ground truth text from mapping
        gt_text = ""
        if ground_truth_map and hasattr(page, "name") and page.name:
            gt_text = ground_truth_map.get(page.name, "")
            if isinstance(gt_text, str):
                gt_text = gt_text if gt_text.strip() else ""
            else:
                gt_text = ""

        return ocr_text, gt_text

    @staticmethod
    def get_page_source_text(page: Optional[Page], is_loading: bool = False) -> str:
        """Get the source text indicator for a page.

        Args:
            page: The page object
            is_loading: Whether OCR is currently loading

        Returns:
            Source text string ("LOADING...", "LABELED", "RAW OCR", etc.)
        """
        if is_loading:
            return "LOADING..."
        elif not page:
            return "(NO PAGE)"
        else:
            # Check if page has a source attribute
            page_source = getattr(page, "page_source", "ocr")
            if page_source == "filesystem":
                return "LABELED"
            elif page_source == "cached_ocr":
                return "CACHED OCR"
            else:
                return "RAW OCR"

    @staticmethod
    def should_update_text_cache(
        current_page_index: int, cached_page_index: int, force: bool = False
    ) -> bool:
        """Determine if the text cache should be updated.

        Args:
            current_page_index: Current page index
            cached_page_index: Index of the cached page
            force: Force cache update regardless of index

        Returns:
            True if cache should be updated, False otherwise
        """
        return force or current_page_index != cached_page_index

    @staticmethod
    def is_page_loaded_for_cache(pages: list, page_index: int) -> bool:
        """Check if a page is loaded and available for caching.

        Args:
            pages: List of pages
            page_index: Index of the page to check

        Returns:
            True if page is loaded and can be cached, False otherwise
        """
        if not (0 <= page_index < len(pages)):
            return False

        page = pages[page_index]
        return page is not None

    @staticmethod
    def get_loading_text() -> Tuple[str, str]:
        """Get loading placeholder text for OCR and ground truth.

        Returns:
            Tuple of (ocr_text, ground_truth_text) with loading placeholders
        """
        return "Loading...", "Loading..."
