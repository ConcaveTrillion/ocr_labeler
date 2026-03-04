"""Tests for line operations."""

from unittest.mock import MagicMock

import pytest
from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.operations.ocr.line_operations import LineOperations


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


def _paragraph(lines: list[Block], y: int) -> Block:
    return Block(
        items=lines,
        bounding_box=_bbox(0, y, 80, y + 20),
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.PARAGRAPH,
    )


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

    def test_copy_ocr_to_ground_truth_no_page(self, operations):
        """Test copying OCR text with no page provided."""
        result = operations.copy_ocr_to_ground_truth(None, 0)

        assert result is False

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

    def test_update_word_ground_truth_success(self, operations, mock_page_with_lines):
        """Test updating ground truth text for a specific word."""
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
        """Test updating ground truth text with invalid word index."""
        result = operations.update_word_ground_truth(
            mock_page_with_lines,
            0,
            99,
            "ignored",
        )

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

    def test_merge_lines_success(self, operations):
        """Test merging multiple lines into the first selected line."""
        line1 = _line([_word("a", "A", 0)], 0)
        line2 = _line([_word("b", "B", 20)], 20)
        line3 = _line([_word("c", "C", 40)], 40)
        page = Page(width=100, height=100, page_index=0, items=[line1, line2, line3])

        expected_word_texts = ["a", "c"]

        result = operations.merge_lines(page, [0, 2])

        assert result is True
        assert len(page.lines) == 2
        assert [word.text for word in page.lines[0].words] == expected_word_texts
        assert page.lines[0].text == "a c"
        assert page.lines[0].ground_truth_text == "A C"

    def test_merge_lines_requires_two_indices(self, operations):
        """Test that merge fails when fewer than two lines are selected."""
        page = Page(
            width=100,
            height=100,
            page_index=0,
            items=[_line([_word("a", "A", 0)], 0), _line([_word("b", "B", 20)], 20)],
        )

        assert operations.merge_lines(page, [0]) is False
        assert operations.merge_lines(page, []) is False

    def test_merge_lines_invalid_index(self, operations):
        """Test that merge fails with out-of-range indices."""
        page = Page(
            width=100,
            height=100,
            page_index=0,
            items=[_line([_word("a", "A", 0)], 0), _line([_word("b", "B", 20)], 20)],
        )

        result = operations.merge_lines(page, [0, 5])

        assert result is False
        assert len(page.lines) == 2

    def test_merge_lines_fails_without_merge_method(self, operations):
        """Test merge fails when selected lines are not Block instances."""
        page = MagicMock(spec=Page)
        page.lines = [MagicMock(), MagicMock()]

        result = operations.merge_lines(page, [0, 1])

        assert result is False

    def test_merge_lines_fails_without_page_removal_api(self, operations):
        """Test merge fails when page does not provide remove_line_if_exists()."""

        class _PageWithoutRemoval:
            def __init__(self):
                self.lines = [
                    _line([_word("a", "A", 0)], 0),
                    _line([_word("b", "B", 20)], 20),
                ]

        page = _PageWithoutRemoval()

        result = operations.merge_lines(page, [0, 1])

        assert result is False

    def test_merge_lines_recomputes_paragraph_bbox_across_paragraphs(self, operations):
        """Merging lines across paragraphs should recompute destination paragraph bbox."""
        line1 = _line([_word("alpha", "A", 0)], 0)
        line2 = _line([_word("beta", "B", 20)], 20)
        para1 = Block(
            items=[line1],
            bounding_box=_bbox(0, 0, 20, 10),
            child_type=BlockChildType.BLOCKS,
            block_category=BlockCategory.PARAGRAPH,
        )
        para2 = Block(
            items=[line2],
            bounding_box=_bbox(20, 0, 40, 10),
            child_type=BlockChildType.BLOCKS,
            block_category=BlockCategory.PARAGRAPH,
        )
        page = Page(width=100, height=100, page_index=0, items=[para1, para2])

        result = operations.merge_lines(page, [0, 1])

        assert result is True
        assert len(page.lines) == 1
        assert len(page.paragraphs) == 1
        merged_paragraph = page.paragraphs[0]
        assert merged_paragraph.bounding_box is not None
        assert merged_paragraph.bounding_box.top_left.x == 0
        assert merged_paragraph.bounding_box.bottom_right.x == 30

    def test_delete_lines_success(self, operations):
        """Test deleting selected lines."""
        line1 = _line([_word("a", "A", 0)], 0)
        line2 = _line([_word("b", "B", 20)], 20)
        line3 = _line([_word("c", "C", 40)], 40)
        page = Page(width=100, height=100, page_index=0, items=[line1, line2, line3])

        result = operations.delete_lines(page, [1, 2])

        assert result is True
        assert len(page.lines) == 1
        assert page.lines[0].text == "a"

    def test_delete_lines_requires_selection(self, operations):
        """Test that deletion fails when no lines are selected."""
        page = Page(
            width=100,
            height=100,
            page_index=0,
            items=[_line([_word("a", "A", 0)], 0), _line([_word("b", "B", 20)], 20)],
        )

        assert operations.delete_lines(page, []) is False

    def test_delete_lines_invalid_index(self, operations):
        """Test that deletion fails with out-of-range indices."""
        page = Page(
            width=100,
            height=100,
            page_index=0,
            items=[_line([_word("a", "A", 0)], 0), _line([_word("b", "B", 20)], 20)],
        )

        result = operations.delete_lines(page, [0, 5])

        assert result is False
        assert len(page.lines) == 2

    def test_delete_lines_fails_without_page_removal_api(self, operations):
        """Test deletion fails when page does not provide remove_line_if_exists()."""

        class _PageWithoutRemoval:
            def __init__(self):
                self.lines = [
                    _line([_word("a", "A", 0)], 0),
                    _line([_word("b", "B", 20)], 20),
                ]

        page = _PageWithoutRemoval()

        result = operations.delete_lines(page, [0])

        assert result is False

    def test_delete_paragraphs_success(self, operations):
        """Deleting selected paragraphs should remove them from the page."""
        para1 = _paragraph([_line([_word("a", "A", 0)], 0)], 0)
        para2 = _paragraph([_line([_word("b", "B", 20)], 20)], 30)
        page = Page(width=100, height=100, page_index=0, items=[para1, para2])

        result = operations.delete_paragraphs(page, [1])

        assert result is True
        assert len(page.paragraphs) == 1
        assert page.paragraphs[0].text == "a"

    def test_delete_words_success(self, operations):
        """Deleting selected words should remove only the targeted words."""
        line = _line(
            [
                _word("alpha", "A", 0),
                _word("beta", "B", 20),
                _word("gamma", "C", 40),
            ],
            0,
        )
        page = Page(width=100, height=100, page_index=0, items=[line])

        result = operations.delete_words(page, [(0, 1)])

        assert result is True
        assert [word.text for word in page.lines[0].words] == ["alpha", "gamma"]

    def test_merge_word_left_success(self, operations):
        """Merging word left should concatenate with immediate left neighbor."""
        line = _line(
            [_word("alpha", "A", 0), _word("beta", "B", 20), _word("gamma", "C", 40)],
            0,
        )
        page = Page(width=100, height=100, page_index=0, items=[line])

        result = operations.merge_word_left(page, 0, 1)

        assert result is True
        assert [word.text for word in page.lines[0].words] == ["alphabeta", "gamma"]
        assert [word.ground_truth_text for word in page.lines[0].words] == ["", ""]
        merged_box = page.lines[0].words[0].bounding_box
        assert merged_box.top_left.x == 0
        assert merged_box.bottom_right.x == 30

    def test_merge_word_right_success(self, operations):
        """Merging word right should concatenate with immediate right neighbor."""
        line = _line(
            [_word("alpha", "A", 0), _word("beta", "B", 20), _word("gamma", "C", 40)],
            0,
        )
        page = Page(width=100, height=100, page_index=0, items=[line])

        result = operations.merge_word_right(page, 0, 1)

        assert result is True
        assert [word.text for word in page.lines[0].words] == ["alpha", "betagamma"]
        assert [word.ground_truth_text for word in page.lines[0].words] == ["", ""]
        merged_box = page.lines[0].words[1].bounding_box
        assert merged_box.top_left.x == 20
        assert merged_box.bottom_right.x == 50

    def test_merge_word_left_fails_for_first_word(self, operations):
        """Merging left on first word should fail."""
        line = _line([_word("alpha", "A", 0), _word("beta", "B", 20)], 0)
        page = Page(width=100, height=100, page_index=0, items=[line])

        result = operations.merge_word_left(page, 0, 0)

        assert result is False
        assert [word.text for word in page.lines[0].words] == ["alpha", "beta"]

    def test_split_word_success(self, operations):
        """Splitting a word should create two words and clear GT for the line."""
        line = _line([_word("alphabet", "ALPHABET", 0), _word("gamma", "GAMMA", 20)], 0)
        page = Page(width=100, height=100, page_index=0, items=[line])

        result = operations.split_word(page, 0, 0, 0.5)

        assert result is True
        assert [word.text for word in page.lines[0].words] == ["alph", "abet", "gamma"]
        assert [word.ground_truth_text for word in page.lines[0].words] == ["", "", ""]

    def test_split_word_rejects_edge_fraction(self, operations):
        """Split should fail when requested at start/end boundaries."""
        line = _line([_word("alpha", "A", 0)], 0)
        page = Page(width=100, height=100, page_index=0, items=[line])

        assert operations.split_word(page, 0, 0, 0.0) is False
        assert operations.split_word(page, 0, 0, 1.0) is False

    def test_split_paragraph_after_line_success(self, operations):
        """Splitting after selected line should split one paragraph into two."""
        line1 = _line([_word("a", "A", 0)], 0)
        line2 = _line([_word("b", "B", 20)], 20)
        para = _paragraph([line1, line2], 0)
        page = Page(width=100, height=100, page_index=0, items=[para])

        result = operations.split_paragraph_after_line(page, 0)

        assert result is True
        assert len(page.paragraphs) == 2
        assert page.paragraphs[0].lines[0].text == "a"
        assert page.paragraphs[1].lines[0].text == "b"

    def test_split_paragraph_after_line_fails_on_last_line(self, operations):
        """Splitting after last line should fail (no trailing segment)."""
        line1 = _line([_word("a", "A", 0)], 0)
        line2 = _line([_word("b", "B", 20)], 20)
        para = _paragraph([line1, line2], 0)
        page = Page(width=100, height=100, page_index=0, items=[para])

        result = operations.split_paragraph_after_line(page, 1)

        assert result is False
        assert len(page.paragraphs) == 1

    def test_split_paragraph_with_selected_lines_success(self, operations):
        """Selected lines should split a paragraph into selected and unselected groups."""
        line1 = _line([_word("a", "A", 0)], 0)
        line2 = _line([_word("b", "B", 20)], 20)
        line3 = _line([_word("c", "C", 40)], 40)
        para = _paragraph([line1, line2, line3], 0)
        page = Page(width=100, height=100, page_index=0, items=[para])

        result = operations.split_paragraph_with_selected_lines(page, [0, 2])

        assert result is True
        assert len(page.paragraphs) == 2
        assert [line.text for line in page.paragraphs[0].lines] == ["a", "c"]
        assert [line.text for line in page.paragraphs[1].lines] == ["b"]

    def test_split_paragraph_with_selected_lines_fails_across_paragraphs(
        self, operations
    ):
        """Split-by-selection should fail when lines span multiple paragraphs."""
        para1 = _paragraph([_line([_word("a", "A", 0)], 0)], 0)
        para2 = _paragraph([_line([_word("b", "B", 20)], 20)], 30)
        page = Page(width=100, height=100, page_index=0, items=[para1, para2])

        result = operations.split_paragraph_with_selected_lines(page, [0, 1])

        assert result is False
        assert len(page.paragraphs) == 2
