"""Tests for text operations."""

from unittest.mock import MagicMock

import pytest
from pd_book_tools.ocr.page import Page

from ocr_labeler.operations.ocr.text_operations import TextOperations


class TestTextOperations:
    """Test TextOperations static methods."""

    def test_get_page_texts_none_page(self):
        """Test getting texts when page is None."""
        ocr_text, gt_text = TextOperations.get_page_texts(None)
        assert ocr_text == ""
        assert gt_text == ""

    def test_get_page_texts_with_ocr_text(self):
        """Test getting texts with OCR text present."""
        page = MagicMock(spec=Page)
        page.text = "Sample OCR text"
        page.name = "test_page"
        ocr_text, gt_text = TextOperations.get_page_texts(page)
        assert ocr_text == "Sample OCR text"
        assert gt_text == ""

    def test_get_page_texts_with_ground_truth(self):
        """Test getting texts with ground truth mapping."""
        page = MagicMock(spec=Page)
        page.text = "Sample OCR text"
        page.name = "test_page"
        ground_truth_map = {"test_page": "Ground truth text"}
        ocr_text, gt_text = TextOperations.get_page_texts(page, ground_truth_map)
        assert ocr_text == "Sample OCR text"
        assert gt_text == "Ground truth text"

    def test_get_page_texts_empty_strings(self):
        """Test getting texts with empty/whitespace strings."""
        page = MagicMock(spec=Page)
        page.text = "   "
        page.name = "test_page"
        ground_truth_map = {"test_page": "\t\n"}
        ocr_text, gt_text = TextOperations.get_page_texts(page, ground_truth_map)
        assert ocr_text == ""
        assert gt_text == ""

    def test_get_page_texts_non_string_values(self):
        """Test getting texts with non-string values."""
        page = MagicMock(spec=Page)
        page.text = 123
        page.name = "test_page"
        ground_truth_map = {"test_page": 456}
        ocr_text, gt_text = TextOperations.get_page_texts(page, ground_truth_map)
        assert ocr_text == ""
        assert gt_text == ""

    def test_get_page_texts_missing_attributes(self):
        """Test getting texts when page attributes are missing."""
        page = MagicMock(spec=Page)  # No text or name attributes set
        ocr_text, gt_text = TextOperations.get_page_texts(page)
        assert ocr_text == ""
        assert gt_text == ""

    @pytest.mark.parametrize(
        "is_loading,page,page_source,expected",
        [
            (True, None, None, "LOADING..."),
            (False, None, None, "(NO PAGE)"),
            (
                False,
                MagicMock(spec=Page, page_source="filesystem"),
                "filesystem",
                "LABELED",
            ),
            (False, MagicMock(spec=Page, page_source="ocr"), "ocr", "RAW OCR"),
            (False, MagicMock(spec=Page), None, "RAW OCR"),  # Default case
        ],
    )
    def test_get_page_source_text(self, is_loading, page, page_source, expected):
        """Test getting page source text with various conditions."""
        if page and page_source:
            page.page_source = page_source

        result = TextOperations.get_page_source_text(page, is_loading)
        assert result == expected

    @pytest.mark.parametrize(
        "current_index,cached_index,force,expected",
        [
            (0, 0, False, False),  # Same index, no force
            (0, 1, False, True),  # Different index, no force
            (0, 0, True, True),  # Same index, force update
            (5, 5, False, False),  # Same index, no force
            (5, 3, False, True),  # Different index, no force
        ],
    )
    def test_should_update_text_cache(
        self, current_index, cached_index, force, expected
    ):
        """Test cache update decision logic."""
        result = TextOperations.should_update_text_cache(
            current_index, cached_index, force
        )
        assert result is expected

    @pytest.mark.parametrize(
        "pages,page_index,expected",
        [
            ([], 0, False),  # Empty pages list - out of bounds
            ([None], 0, False),  # Page is None - not loaded
            ([MagicMock(spec=Page)], 0, True),  # Valid page - loaded
            ([MagicMock(spec=Page)], -1, False),  # Negative index - out of bounds
            ([MagicMock(spec=Page)], 1, False),  # Index out of bounds - not loaded
            ([None, MagicMock(spec=Page)], 1, True),  # Valid page at index 1 - loaded
        ],
    )
    def test_is_page_loaded_for_cache(self, pages, page_index, expected):
        """Test checking if page is loaded for caching."""
        result = TextOperations.is_page_loaded_for_cache(pages, page_index)
        assert result is expected

    def test_get_loading_text(self):
        """Test getting loading placeholder text."""
        ocr_text, gt_text = TextOperations.get_loading_text()
        assert ocr_text == "Loading..."
        assert gt_text == "Loading..."
