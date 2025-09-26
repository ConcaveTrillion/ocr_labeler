"""Tests for line operations."""

from unittest.mock import MagicMock

import pytest
from pd_book_tools.ocr.page import Page

from ocr_labeler.operations.ocr.line_operations import LineOperations


class TestLineOperations:
    """Test LineOperations class methods."""

    @pytest.fixture
    def operations(self):
        """Create LineOperations instance for testing."""
        return LineOperations()

    @pytest.fixture
    def mock_page_with_lines(self):
        """Create a mock page with lines and words."""
        page = MagicMock(spec=Page)

        # Create mock lines
        line1 = MagicMock()
        line2 = MagicMock()

        # Create mock words for line 1
        word1 = MagicMock()
        word1.text = "hello"
        word1.ground_truth_text = "Hello"

        word2 = MagicMock()
        word2.text = "world"
        word2.ground_truth_text = "World"

        line1.words = [word1, word2]

        # Create mock words for line 2 (no ground truth)
        word3 = MagicMock()
        word3.text = "test"
        word3.ground_truth_text = ""

        line2.words = [word3]

        page.lines = [line1, line2]
        return page

    def test_copy_ground_truth_to_ocr_success(self, operations, mock_page_with_lines):
        """Test successfully copying ground truth to OCR text."""
        result = operations.copy_ground_truth_to_ocr(mock_page_with_lines, 0)

        assert result is True
        # Verify words were updated
        line1 = mock_page_with_lines.lines[0]
        assert line1.words[0].text == "Hello"
        assert line1.words[1].text == "World"

    def test_copy_ground_truth_to_ocr_no_ground_truth(
        self, operations, mock_page_with_lines
    ):
        """Test copying ground truth when no ground truth exists."""
        result = operations.copy_ground_truth_to_ocr(mock_page_with_lines, 1)

        assert result is False
        # Verify word was not changed
        line2 = mock_page_with_lines.lines[1]
        assert line2.words[0].text == "test"

    def test_copy_ground_truth_to_ocr_invalid_line_index(
        self, operations, mock_page_with_lines
    ):
        """Test copying ground truth with invalid line index."""
        result = operations.copy_ground_truth_to_ocr(mock_page_with_lines, 5)

        assert result is False

    def test_copy_ground_truth_to_ocr_no_page(self, operations):
        """Test copying ground truth with no page provided."""
        result = operations.copy_ground_truth_to_ocr(None, 0)

        assert result is False

    def test_copy_ground_truth_to_ocr_no_lines(self, operations):
        """Test copying ground truth when page has no lines."""
        page = MagicMock(spec=Page)
        page.lines = []
        result = operations.copy_ground_truth_to_ocr(page, 0)

        assert result is False

    def test_copy_ocr_to_ground_truth_success(self, operations, mock_page_with_lines):
        """Test successfully copying OCR text to ground truth."""
        result = operations.copy_ocr_to_ground_truth(mock_page_with_lines, 0)

        assert result is True
        # Verify words were updated
        line1 = mock_page_with_lines.lines[0]
        assert line1.words[0].ground_truth_text == "hello"
        assert line1.words[1].ground_truth_text == "world"

    def test_copy_ocr_to_ground_truth_no_ocr_text(self, operations):
        """Test copying OCR text when no OCR text exists."""
        page = MagicMock(spec=Page)
        line = MagicMock()
        word = MagicMock()
        word.text = ""
        word.ground_truth_text = ""
        line.words = [word]
        page.lines = [line]

        result = operations.copy_ocr_to_ground_truth(page, 0)

        assert result is False

    def test_clear_ground_truth_for_line_no_ground_truth(self, operations):
        """Test clearing ground truth when none exists."""
        page = MagicMock(spec=Page)
        line = MagicMock()
        word = MagicMock()
        word.ground_truth_text = ""
        line.words = [word]
        page.lines = [line]

        result = operations.clear_ground_truth_for_line(page, 0)

        assert result is False

    def test_validate_line_consistency_exact_matches(self, operations):
        """Test validating line with exact matches."""
        page = MagicMock(spec=Page)
        line = MagicMock()
        word = MagicMock()
        word.text = "hello"
        word.ground_truth_text = "hello"
        line.words = [word]
        page.lines = [line]

        result = operations.validate_line_consistency(page, 0)

        assert result["valid"] is True
        assert result["words"] == 1
        assert result["with_gt"] == 1
        assert result["matches"] == 1
        assert result["mismatches"] == 0
        assert result["accuracy"] == 1.0

    def test_validate_line_consistency_no_ground_truth(self, operations):
        """Test validating line with no ground truth."""
        page = MagicMock(spec=Page)
        line = MagicMock()
        word = MagicMock()
        word.text = "hello"
        word.ground_truth_text = ""
        line.words = [word]
        page.lines = [line]

        result = operations.validate_line_consistency(page, 0)

        assert result["valid"] is True
        assert result["words"] == 1
        assert result["with_gt"] == 0
        assert result["matches"] == 0
        assert result["mismatches"] == 0
        assert result["accuracy"] == 1.0  # No GT means 100% accuracy

    def test_validate_line_consistency_empty_line(self, operations):
        """Test validating empty line."""
        page = MagicMock(spec=Page)
        line = MagicMock()
        line.words = []
        page.lines = [line]

        result = operations.validate_line_consistency(page, 0)

        assert result["valid"] is True
        assert result["words"] == 0
        assert result["with_gt"] == 0
        assert result["matches"] == 0
        assert result["mismatches"] == 0

    def test_clear_ground_truth_for_line_success(
        self, operations, mock_page_with_lines
    ):
        """Test successfully clearing ground truth for a line."""
        result = operations.clear_ground_truth_for_line(mock_page_with_lines, 0)

        assert result is True
        # Verify ground truth was cleared
        line1 = mock_page_with_lines.lines[0]
        assert line1.words[0].ground_truth_text == ""
        assert line1.words[1].ground_truth_text == ""

    def test_clear_ground_truth_for_line_invalid_index(
        self, operations, mock_page_with_lines
    ):
        """Test clearing ground truth with invalid line index."""
        result = operations.clear_ground_truth_for_line(mock_page_with_lines, 10)

        assert result is False

    def test_validate_line_consistency_success(self, operations, mock_page_with_lines):
        """Test validating line consistency successfully."""
        result = operations.validate_line_consistency(mock_page_with_lines, 0)

        assert result["valid"] is True
        assert result["words"] == 2
        assert result["with_gt"] == 2
        assert result["matches"] == 0  # OCR != GT (case difference)
        assert result["mismatches"] == 2
        assert len(result["mismatch_details"]) == 2
        assert result["accuracy"] == 0.0

    def test_validate_line_consistency_invalid_line_index(
        self, operations, mock_page_with_lines
    ):
        """Test validating line with invalid index."""
        result = operations.validate_line_consistency(mock_page_with_lines, 10)

        assert result["valid"] is False
        assert "out of range" in result["error"]

    def test_validate_line_consistency_no_page(self, operations):
        """Test validating line with no page."""
        result = operations.validate_line_consistency(None, 0)

        assert result["valid"] is False
        assert result["error"] == "No page provided"

    def test_validate_line_consistency_exception_handling(self, operations):
        """Test validating line with exception handling."""
        page = MagicMock(spec=Page)
        # Create a line that will cause an exception when accessing words
        line = MagicMock()
        line.words.side_effect = Exception("Test exception")
        page.lines = [line]

        result = operations.validate_line_consistency(page, 0)

        # The method uses getattr with default, so exceptions are handled gracefully
        # It should return a valid result with 0 words
        assert result["valid"] is True
        assert result["words"] == 0
        assert result["with_gt"] == 0
        assert result["matches"] == 0
        assert result["mismatches"] == 0
