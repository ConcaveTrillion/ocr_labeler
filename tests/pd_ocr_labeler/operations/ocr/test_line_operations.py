"""Tests for LineOperations ground-truth editing methods."""

from unittest.mock import MagicMock

import pytest
from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from pd_ocr_labeler.operations.ocr.line_operations import LineOperations


def _configure_mock_page(page):
    """Wire up validated_line_words on a MagicMock(spec=Page)."""

    def _validated_line_words(line_index):
        lines = page.lines
        if line_index < 0 or line_index >= len(lines):
            return None
        return list(lines[line_index].words)

    page.validated_line_words = _validated_line_words
    return page


def _bbox(x1: int, y1: int, x2: int, y2: int) -> BoundingBox:
    return BoundingBox(Point(x1, y1), Point(x2, y2), is_normalized=False)


def _word(text: str, gt: str | None, x: int) -> Word:
    return Word(
        text=text,
        bounding_box=_bbox(x, 0, x + 10, 10),
        ocr_confidence=1.0,
        ground_truth_text=gt,
    )


def _line(words: list[Word], x: int) -> Block:
    return Block(
        items=words,
        bounding_box=_bbox(x, 0, x + 20, 10),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
    )


class TestLineOperations:
    """Test LineOperations ground-truth editing methods."""

    @pytest.fixture
    def operations(self):
        return LineOperations()

    @pytest.fixture
    def mock_page_with_lines(self):
        """Create a page with real Block and Word objects."""
        word1 = _word("hello", "Hello", 0)
        word2 = _word("world", "World", 20)
        line1 = _line([word1, word2], 0)

        word3 = _word("test", "", 0)
        line2 = _line([word3], 40)

        return Page(width=100, height=100, page_index=0, items=[line1, line2])

    # ------------------------------------------------------------------
    # copy_ground_truth_to_ocr
    # ------------------------------------------------------------------

    def test_copy_ground_truth_to_ocr_success(self, operations, mock_page_with_lines):
        """Successfully copies ground truth to OCR text."""
        result = operations.copy_ground_truth_to_ocr(mock_page_with_lines, 0)

        assert result is True
        line1 = mock_page_with_lines.lines[0]
        assert line1.words[0].text == "Hello"
        assert line1.words[1].text == "World"

    def test_copy_ground_truth_to_ocr_no_ground_truth(
        self, operations, mock_page_with_lines
    ):
        """Copying ground truth when none exists returns False."""
        result = operations.copy_ground_truth_to_ocr(mock_page_with_lines, 1)

        assert result is False
        line2 = mock_page_with_lines.lines[1]
        assert line2.words[0].text == "test"

    def test_copy_ground_truth_to_ocr_invalid_line_index(
        self, operations, mock_page_with_lines
    ):
        """Copying ground truth with invalid line index returns False."""
        result = operations.copy_ground_truth_to_ocr(mock_page_with_lines, 5)

        assert result is False

    def test_copy_ground_truth_to_ocr_no_page(self, operations):
        """Copying ground truth with no page returns False."""
        result = operations.copy_ground_truth_to_ocr(None, 0)

        assert result is False

    def test_copy_ground_truth_to_ocr_no_lines(self, operations):
        """Copying ground truth when page has no lines returns False."""
        page = MagicMock(spec=Page)
        page.lines = []
        _configure_mock_page(page)
        result = operations.copy_ground_truth_to_ocr(page, 0)

        assert result is False

    # ------------------------------------------------------------------
    # copy_ocr_to_ground_truth
    # ------------------------------------------------------------------

    def test_copy_ocr_to_ground_truth_success(self, operations, mock_page_with_lines):
        """Successfully copies OCR text to ground truth."""
        result = operations.copy_ocr_to_ground_truth(mock_page_with_lines, 0)

        assert result is True
        line1 = mock_page_with_lines.lines[0]
        assert line1.words[0].ground_truth_text == "hello"
        assert line1.words[1].ground_truth_text == "world"

    def test_copy_ocr_to_ground_truth_no_page(self, operations):
        """Copying OCR text with no page returns False."""
        result = operations.copy_ocr_to_ground_truth(None, 0)

        assert result is False

    def test_copy_ocr_to_ground_truth_no_ocr_text(self, operations):
        """Copying OCR text when no OCR text exists returns False."""
        line = _line([_word("", "", 0)], 0)
        page = Page(width=100, height=100, page_index=0, items=[line])

        result = operations.copy_ocr_to_ground_truth(page, 0)

        assert result is False

    # ------------------------------------------------------------------
    # copy_selected_words_ocr_to_ground_truth
    # ------------------------------------------------------------------

    def test_copy_selected_words_ocr_to_ground_truth_selected_only(
        self, operations, mock_page_with_lines
    ):
        """Copy OCR->GT updates only explicitly selected words."""
        line1 = mock_page_with_lines.lines[0]
        line2 = mock_page_with_lines.lines[1]

        line1.words[0].ground_truth_text = "keep-gt-0"
        line1.words[1].ground_truth_text = "keep-gt-1"
        line2.words[0].ground_truth_text = "keep-gt-2"

        result = operations.copy_selected_words_ocr_to_ground_truth(
            mock_page_with_lines,
            [(0, 1), (1, 0)],
        )

        assert result is True
        assert line1.words[0].ground_truth_text == "keep-gt-0"
        assert line1.words[1].ground_truth_text == "world"
        assert line2.words[0].ground_truth_text == "test"

    def test_copy_selected_words_ocr_to_ground_truth_returns_false_when_no_updates(
        self, operations, mock_page_with_lines
    ):
        """Copy OCR->GT fails when selected words have no OCR text."""
        line1 = mock_page_with_lines.lines[0]
        line1.words[1].text = ""
        line1.words[1].ground_truth_text = "unchanged"

        result = operations.copy_selected_words_ocr_to_ground_truth(
            mock_page_with_lines,
            [(0, 1)],
        )

        assert result is False
        assert line1.words[1].ground_truth_text == "unchanged"

    # ------------------------------------------------------------------
    # update_word_ground_truth
    # ------------------------------------------------------------------

    def test_update_word_ground_truth_success(self, operations, mock_page_with_lines):
        """Updates ground truth text for a specific word."""
        result = operations.update_word_ground_truth(
            mock_page_with_lines,
            0,
            1,
            "updated-world",
        )

        assert result is True
        line1 = mock_page_with_lines.lines[0]
        assert line1.words[1].ground_truth_text == "updated-world"

    def test_update_word_ground_truth_invalid_word_index(
        self,
        operations,
        mock_page_with_lines,
    ):
        """Updating ground truth with invalid word index returns False."""
        result = operations.update_word_ground_truth(
            mock_page_with_lines,
            0,
            99,
            "ignored",
        )

        assert result is False

    # ------------------------------------------------------------------
    # update_word_attributes
    # ------------------------------------------------------------------

    def test_update_word_attributes_success(self, operations):
        """Updates style attributes for a specific word."""
        line = _line([_word("hello", "Hello", 0), _word("world", "World", 20)], 0)
        page = Page(width=100, height=100, page_index=0, items=[line])

        result = operations.update_word_attributes(
            page,
            0,
            1,
            italic=True,
            small_caps=True,
            blackletter=False,
            left_footnote=False,
            right_footnote=False,
        )

        assert result is True
        assert "italics" in page.lines[0].words[1].text_style_labels
        assert "small caps" in page.lines[0].words[1].text_style_labels
        assert "blackletter" not in page.lines[0].words[1].text_style_labels

    def test_update_word_attributes_invalid_word_index(
        self,
        operations,
        mock_page_with_lines,
    ):
        """Updating style attributes with invalid word index returns False."""
        result = operations.update_word_attributes(
            mock_page_with_lines,
            0,
            99,
            italic=True,
            small_caps=False,
            blackletter=False,
            left_footnote=False,
            right_footnote=False,
        )

        assert result is False

    # ------------------------------------------------------------------
    # clear_ground_truth_for_line
    # ------------------------------------------------------------------

    def test_clear_ground_truth_for_line_no_ground_truth(self, operations):
        """Clearing ground truth when none exists returns False."""
        line = _line([_word("test", "", 0)], 0)
        page = Page(width=100, height=100, page_index=0, items=[line])

        result = operations.clear_ground_truth_for_line(page, 0)

        assert result is False

    def test_clear_ground_truth_for_line_success(
        self, operations, mock_page_with_lines
    ):
        """Successfully clears ground truth for a line."""
        result = operations.clear_ground_truth_for_line(mock_page_with_lines, 0)

        assert result is True
        line1 = mock_page_with_lines.lines[0]
        assert line1.words[0].ground_truth_text == ""
        assert line1.words[1].ground_truth_text == ""

    def test_clear_ground_truth_for_line_invalid_index(
        self, operations, mock_page_with_lines
    ):
        """Clearing ground truth with invalid line index returns False."""
        result = operations.clear_ground_truth_for_line(mock_page_with_lines, 10)

        assert result is False

    # ------------------------------------------------------------------
    # validate_line_consistency (Block method, exercised for coverage)
    # ------------------------------------------------------------------

    def test_validate_line_consistency_exact_matches(self, operations):
        """Line with exact OCR/GT matches reports correctly."""
        word = Word(
            text="hello",
            bounding_box=BoundingBox.from_ltrb(0, 0, 10, 10),
            ground_truth_text="hello",
        )
        line = Block(
            items=[word],
            child_type=BlockChildType.WORDS,
            block_category=BlockCategory.LINE,
        )

        result = line.validate_line_consistency()

        assert result["valid"] is True
        assert result["words"] == 1
        assert result["with_gt"] == 1
        assert result["matches"] == 1
        assert result["mismatches"] == 0
        assert result["accuracy"] == 1.0

    def test_validate_line_consistency_no_ground_truth(self, operations):
        """Line with no GT reports 100% accuracy."""
        word = Word(
            text="hello",
            bounding_box=BoundingBox.from_ltrb(0, 0, 10, 10),
            ground_truth_text="",
        )
        line = Block(
            items=[word],
            child_type=BlockChildType.WORDS,
            block_category=BlockCategory.LINE,
        )

        result = line.validate_line_consistency()

        assert result["valid"] is True
        assert result["words"] == 1
        assert result["with_gt"] == 0
        assert result["accuracy"] == 1.0

    def test_validate_line_consistency_empty_line(self, operations):
        """Empty line reports zero counts."""
        line = Block(
            items=[],
            child_type=BlockChildType.WORDS,
            block_category=BlockCategory.LINE,
        )

        result = line.validate_line_consistency()

        assert result["valid"] is True
        assert result["words"] == 0
        assert result["with_gt"] == 0
        assert result["matches"] == 0
        assert result["mismatches"] == 0
