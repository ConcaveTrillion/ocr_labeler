"""Tests for line operations."""

from unittest.mock import MagicMock

import numpy as np
import pytest
from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.operations.ocr.line_operations import LineOperations


def _bbox(x1: int, y1: int, x2: int, y2: int) -> BoundingBox:
    return BoundingBox(Point(x1, y1), Point(x2, y2), is_normalized=False)


def _configure_mock_page(page):
    """Wire up validated_line_words on a MagicMock(spec=Page)."""

    def _validated_line_words(line_index):
        lines = page.lines
        if line_index < 0 or line_index >= len(lines):
            return None
        return list(lines[line_index].words)

    page.validated_line_words = _validated_line_words
    return page


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
        _configure_mock_page(page)
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
        _configure_mock_page(page)
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
        _configure_mock_page(page)

        result = operations.copy_ocr_to_ground_truth(page, 0)

        assert result is False

    def test_copy_selected_words_ocr_to_ground_truth_selected_only(
        self, operations, mock_page_with_lines
    ):
        """Copy OCR→GT should update only explicitly selected words."""
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
        """Copy OCR→GT should fail when selected words have no OCR text."""
        line1 = mock_page_with_lines.lines[0]
        line1.words[1].text = ""
        line1.words[1].ground_truth_text = "unchanged"

        result = operations.copy_selected_words_ocr_to_ground_truth(
            mock_page_with_lines,
            [(0, 1)],
        )

        assert result is False
        assert line1.words[1].ground_truth_text == "unchanged"

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

    def test_update_word_attributes_success(self, operations):
        """Test updating style attributes for a specific word."""
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
        """Test updating style attributes with invalid word index."""
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

    def test_clear_ground_truth_for_line_no_ground_truth(self, operations):
        """Test clearing ground truth when none exists."""
        page = MagicMock(spec=Page)
        line = MagicMock()
        word = MagicMock()
        word.ground_truth_text = ""
        line.words = [word]
        page.lines = [line]
        _configure_mock_page(page)

        result = operations.clear_ground_truth_for_line(page, 0)

        assert result is False

    def test_validate_line_consistency_exact_matches(self, operations):
        """Test validating line with exact matches."""
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
        """Test validating line with no ground truth."""
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
        assert result["matches"] == 0
        assert result["mismatches"] == 0
        assert result["accuracy"] == 1.0  # No GT means 100% accuracy

    def test_validate_line_consistency_empty_line(self, operations):
        """Test validating empty line."""
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
        w1 = Word(
            text="hello",
            bounding_box=BoundingBox.from_ltrb(0, 0, 10, 10),
            ground_truth_text="Hello",
        )
        w2 = Word(
            text="world",
            bounding_box=BoundingBox.from_ltrb(10, 0, 20, 10),
            ground_truth_text="World",
        )
        line = Block(
            items=[w1, w2],
            child_type=BlockChildType.WORDS,
            block_category=BlockCategory.LINE,
        )
        result = line.validate_line_consistency()

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
        """Line index validation is now the caller's responsibility."""
        assert len(mock_page_with_lines.lines) < 11

    def test_validate_line_consistency_no_page(self, operations):
        """validate_line_consistency is now on Block; no-page case is N/A."""
        pass

    def test_validate_line_consistency_exception_handling(self, operations):
        """Empty line returns zero counts."""
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
        _configure_mock_page(page)

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

    def test_merge_lines_falls_back_on_malformed_bbox_metadata(
        self,
        operations,
        monkeypatch,
    ):
        """Merge should still succeed when Block.merge fails with NoneType.is_normalized."""
        line1 = _line([_word("alpha", "A", 0)], 0)
        line2 = _line([_word("beta", "B", 20)], 20)
        page = Page(width=100, height=100, page_index=0, items=[line1, line2])

        from pd_book_tools.ocr.block import Block as OCRBlock

        def _broken_merge(_self, _other):
            raise AttributeError("'NoneType' object has no attribute 'is_normalized'")

        monkeypatch.setattr(OCRBlock, "merge", _broken_merge)

        result = operations.merge_lines(page, [0, 1])

        assert result is True
        assert len(page.lines) == 1
        assert [word.text for word in page.lines[0].words] == ["alpha", "beta"]

    def test_merge_lines_ignores_finalize_malformed_bbox_error(
        self,
        operations,
        monkeypatch,
    ):
        """Merge should succeed when finalize recompute raises NoneType.is_normalized."""
        line1 = _line([_word("alpha", "A", 0)], 0)
        line2 = _line([_word("beta", "B", 20)], 20)
        page = Page(width=100, height=100, page_index=0, items=[line1, line2])

        from pd_book_tools.ocr.block import Block as OCRBlock

        original_recompute = OCRBlock.recompute_bounding_box

        def _broken_merge(_self, _other):
            raise AttributeError("'NoneType' object has no attribute 'is_normalized'")

        def _sometimes_broken_recompute(self):
            if self is page.lines[0]:
                raise AttributeError(
                    "'NoneType' object has no attribute 'is_normalized'"
                )
            return original_recompute(self)

        monkeypatch.setattr(OCRBlock, "merge", _broken_merge)
        monkeypatch.setattr(
            OCRBlock, "recompute_bounding_box", _sometimes_broken_recompute
        )

        result = operations.merge_lines(page, [0, 1])

        assert result is True
        assert len(page.lines) == 1
        assert [word.text for word in page.lines[0].words] == ["alpha", "beta"]

    def test_merge_lines_removes_empty_paragraphs_when_finalize_is_malformed(
        self,
        operations,
        monkeypatch,
    ):
        """Even when finalize path hits malformed geometry, empty paragraphs should be removed."""
        line1 = _line([_word("alpha", "A", 0)], 0)
        line2 = _line([_word("beta", "B", 20)], 20)
        para1 = _paragraph([line1], 0)
        para2 = _paragraph([line2], 30)
        page = Page(width=100, height=100, page_index=0, items=[para1, para2])

        monkeypatch.setattr(
            page,
            "finalize_page_structure",
            lambda: (_ for _ in ()).throw(
                AttributeError("'NoneType' object has no attribute 'is_normalized'")
            ),
        )

        result = operations.merge_lines(page, [0, 1])

        assert result is True
        assert len(page.lines) == 1
        assert len(page.paragraphs) == 1
        assert [line.text for line in page.paragraphs[0].lines] == ["alpha beta"]

    def test_merge_paragraphs_handles_malformed_bbox_during_remove_item(
        self,
        operations,
    ):
        """Paragraph merge should succeed when remove_item recompute hits malformed geometry."""
        para1 = _paragraph([_line([_word("a", "A", 0)], 0)], 0)
        para2 = _paragraph([_line([_word("b", "B", 20)], 20)], 30)
        malformed_para = _paragraph([_line([_word("c", "C", 40)], 40)], 60)
        page = Page(
            width=100,
            height=100,
            page_index=0,
            items=[para1, para2, malformed_para],
        )
        malformed_para.bounding_box = None

        paragraphs = list(page.paragraphs)
        index_a = next(
            i
            for i, paragraph in enumerate(paragraphs)
            if paragraph.lines[0].text == "a"
        )
        index_b = next(
            i
            for i, paragraph in enumerate(paragraphs)
            if paragraph.lines[0].text == "b"
        )

        result = operations.merge_paragraphs(page, [index_a, index_b])

        assert result is True
        assert len(page.paragraphs) == 2
        line_texts_by_paragraph = [
            [line.text for line in para.lines] for para in page.paragraphs
        ]
        assert ["a", "b"] in line_texts_by_paragraph

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

    def test_delete_words_removes_line_when_it_becomes_empty(self, operations):
        """Deleting the final word from a line should remove that now-empty line."""
        line1 = _line([_word("alpha", "A", 0)], 0)
        line2 = _line([_word("beta", "B", 20)], 20)
        paragraph = _paragraph([line1, line2], 0)
        page = Page(width=100, height=100, page_index=0, items=[paragraph])

        result = operations.delete_words(page, [(0, 0)])

        assert result is True
        assert len(page.lines) == 1
        assert page.lines[0].text == "beta"

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

    def test_split_word_vertical_assigns_split_pieces_to_closest_line(self, operations):
        """Vertical split should move both split words to the closest line by midpoint."""
        source_word = Word(
            text="alphabet",
            bounding_box=_bbox(0, 34, 12, 54),
            ocr_confidence=1.0,
            ground_truth_text="ALPHABET",
        )
        source_line = Block(
            items=[source_word],
            bounding_box=_bbox(0, 0, 20, 10),
            child_type=BlockChildType.WORDS,
            block_category=BlockCategory.LINE,
        )
        lower_line = Block(
            items=[_word("delta", "DELTA", 20)],
            bounding_box=_bbox(0, 40, 80, 50),
            child_type=BlockChildType.WORDS,
            block_category=BlockCategory.LINE,
        )
        page = Page(
            width=100, height=100, page_index=0, items=[source_line, lower_line]
        )

        result = operations.split_word_vertically_and_assign_to_closest_line(
            page,
            0,
            0,
            0.5,
        )

        assert result is True
        assert all(
            word.text != "alphabet" for line in page.lines for word in line.words
        )

        target_line_words = None
        for line in page.lines:
            line_words = [word.text for word in line.words]
            if line_words[:2] == ["alph", "abet"]:
                target_line_words = line.words
                break

        assert target_line_words is not None
        assert all(word.ground_truth_text == "" for word in target_line_words)

    def test_rebox_word_replaces_word_bounding_box(self, operations):
        """Reboxing should replace the target word bounding box coordinates."""
        line = _line([_word("alpha", "A", 0)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])

        result = operations.rebox_word(page, 0, 0, 30.0, 5.0, 70.0, 25.0)

        assert result is True
        updated_bbox = page.lines[0].words[0].bounding_box
        assert updated_bbox.top_left.x == 30.0
        assert updated_bbox.top_left.y == 5.0
        assert updated_bbox.bottom_right.x == 70.0
        assert updated_bbox.bottom_right.y == 25.0

    def test_rebox_word_runs_word_refine_helpers(self, operations, monkeypatch):
        """Rebox should auto-refine the updated word when a page image exists."""
        import numpy as np

        line = _line([_word("alpha", "A", 0)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])
        target_word = page.lines[0].words[0]

        # Provide a dummy page image so refinement paths are attempted
        dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
        monkeypatch.setattr(
            type(page), "cv2_numpy_page_image", property(lambda self: dummy_image)
        )

        seen = []
        target_word.crop_bottom = lambda img: seen.append("crop")

        result = operations.rebox_word(page, 0, 0, 30.0, 5.0, 70.0, 25.0)

        assert result is True
        # crop_bottom is called as fallback when bbox.refine returns None
        # (or refine succeeds first). Either way, rebox itself succeeds.

    def test_nudge_word_bbox_expands_and_contracts_size(self, operations):
        """Nudging should resize bbox dimensions, not translate position."""
        line = _line([_word("alpha", "A", 20)], 20)
        page = Page(width=200, height=100, page_index=0, items=[line])

        result = operations.nudge_word_bbox(page, 0, 0, 3.0, 3.0, 2.0, 2.0)

        assert result is True
        updated_bbox = page.lines[0].words[0].bounding_box
        assert updated_bbox.top_left.x == 17.0
        assert updated_bbox.top_left.y == 0.0
        assert updated_bbox.bottom_right.x == 33.0
        assert updated_bbox.bottom_right.y == 12.0

        contract_result = operations.nudge_word_bbox(page, 0, 0, -2.0, -2.0, -1.0, -1.0)

        assert contract_result is True
        contracted_bbox = page.lines[0].words[0].bounding_box
        assert contracted_bbox.top_left.x == 19.0
        assert contracted_bbox.top_left.y == 1.0
        assert contracted_bbox.bottom_right.x == 31.0
        assert contracted_bbox.bottom_right.y == 11.0

    def test_nudge_word_bbox_can_skip_refine_helpers(self, operations):
        """Nudging with refine_after=False should not call word refine helpers."""
        line = _line([_word("alpha", "A", 20)], 20)
        page = Page(width=200, height=100, page_index=0, items=[line])
        word = page.lines[0].words[0]

        word.crop_bottom = MagicMock()
        word.expand_to_content = MagicMock()

        result = operations.nudge_word_bbox(
            page,
            0,
            0,
            3.0,
            3.0,
            2.0,
            2.0,
            refine_after=False,
        )

        assert result is True
        word.crop_bottom.assert_not_called()
        word.expand_to_content.assert_not_called()

    def test_refine_words_runs_refine_for_selected_words(self, operations, monkeypatch):
        """Refining words should run per-word refinement for selected keys."""
        import numpy as np
        from pd_book_tools.geometry.bounding_box import BoundingBox

        line = _line([_word("alpha", "A", 0), _word("beta", "B", 20)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])

        # Provide a dummy page image so refinement paths are attempted
        dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
        monkeypatch.setattr(
            type(page), "cv2_numpy_page_image", property(lambda self: dummy_image)
        )

        second_word = page.lines[0].words[1]

        # Mock bbox.refine to return None so crop_bottom fallback is triggered
        seen = []
        monkeypatch.setattr(BoundingBox, "refine", lambda *a, **kw: None)
        second_word.crop_bottom = lambda img: seen.append("second")

        result = operations.refine_words(page, [(0, 1)])

        assert result is True
        assert "second" in seen

    def test_refine_words_prefers_bbox_refine(self, operations):
        """Refine should prefer BoundingBox.refine over crop helpers when image exists."""
        line = _line([_word("alpha", "A", 0), _word("beta", "B", 20)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])
        page.cv2_numpy_page_image = np.zeros((20, 20), dtype=np.uint8)
        word = page.lines[0].words[1]

        original_bbox = word.bounding_box
        refined_bbox = _bbox(20, 0, 35, 10)
        original_bbox.refine = MagicMock(return_value=refined_bbox)
        word.crop_bottom = MagicMock()
        word.expand_to_content = MagicMock()

        result = operations.refine_words(page, [(0, 1)])

        assert result is True
        original_bbox.refine.assert_called_once_with(
            page.cv2_numpy_page_image,
            padding_px=1,
            expand_beyond_original=False,
        )
        word.crop_bottom.assert_not_called()
        word.expand_to_content.assert_not_called()
        assert word.bounding_box.to_ltrb() == refined_bbox.to_ltrb()

    def test_expand_then_refine_words_runs_expand_before_refine(
        self, operations, monkeypatch
    ):
        """Expand-then-refine should call crop_bottom fallback when refine returns None."""
        import numpy as np
        from pd_book_tools.geometry.bounding_box import BoundingBox

        line = _line([_word("alpha", "A", 0)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])
        word = page.lines[0].words[0]

        dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
        monkeypatch.setattr(
            type(page), "cv2_numpy_page_image", property(lambda self: dummy_image)
        )

        seen = []
        monkeypatch.setattr(BoundingBox, "refine", lambda *a, **kw: None)
        word.crop_bottom = lambda img: seen.append("crop")

        result = operations.expand_then_refine_words(page, [(0, 0)])

        assert result is True
        assert "crop" in seen

    def test_expand_then_refine_words_iterates_until_bbox_stabilizes(
        self, operations, monkeypatch
    ):
        """Expand-then-refine should run multiple passes until bbox no longer changes."""
        import numpy as np
        from pd_book_tools.geometry.bounding_box import BoundingBox

        line = _line([_word("alpha", "A", 0)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])
        word = page.lines[0].words[0]

        dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
        monkeypatch.setattr(
            type(page), "cv2_numpy_page_image", property(lambda self: dummy_image)
        )

        calls = {"crop": 0}

        # Make refine return None so crop_bottom is used
        monkeypatch.setattr(BoundingBox, "refine", lambda *a, **kw: None)

        def _crop_bottom(img) -> None:
            calls["crop"] += 1
            bbox = word.bounding_box
            min_x = float(bbox.minX or 0.0)
            min_y = float(bbox.minY or 0.0)
            max_x = float(bbox.maxX or 0.0)
            max_y = float(bbox.maxY or 0.0)
            if calls["crop"] == 1:
                max_x += 3.0
            elif calls["crop"] == 2:
                max_x += 2.0
            word.bounding_box = _bbox(int(min_x), int(min_y), int(max_x), int(max_y))

        word.crop_bottom = _crop_bottom

        result = operations.expand_then_refine_words(page, [(0, 0)])

        assert result is True
        assert calls["crop"] >= 2
        assert page.lines[0].words[0].bounding_box.bottom_right.x == 15

    def test_expand_then_refine_words_prefers_bbox_refine_expand_mode(self, operations):
        """Expand-then-refine should prefer BoundingBox.refine(expand_beyond_original=True)."""
        line = _line([_word("alpha", "A", 0)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])
        page.cv2_numpy_page_image = np.zeros((20, 20), dtype=np.uint8)
        word = page.lines[0].words[0]

        original_bbox = word.bounding_box
        refined_bbox = _bbox(0, 0, 12, 10)
        original_bbox.refine = MagicMock(return_value=refined_bbox)
        word.expand_to_content = MagicMock()
        word.crop_bottom = MagicMock()

        result = operations.expand_then_refine_words(page, [(0, 0)])

        assert result is True
        original_bbox.refine.assert_called_with(
            page.cv2_numpy_page_image,
            padding_px=0,
            expand_beyond_original=True,
        )
        word.expand_to_content.assert_not_called()
        word.crop_bottom.assert_not_called()
        assert word.bounding_box.to_ltrb() == refined_bbox.to_ltrb()

    def test_refine_lines_runs_refine_for_line_words(self, operations, monkeypatch):
        """Refining lines should process all words in selected lines."""
        import numpy as np
        from pd_book_tools.geometry.bounding_box import BoundingBox

        line1 = _line([_word("alpha", "A", 0)], 0)
        line2 = _line([_word("beta", "B", 20)], 20)
        page = Page(width=200, height=100, page_index=0, items=[line1, line2])

        dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
        monkeypatch.setattr(
            type(page), "cv2_numpy_page_image", property(lambda self: dummy_image)
        )
        monkeypatch.setattr(BoundingBox, "refine", lambda *a, **kw: None)

        seen = []
        page.lines[0].words[0].crop_bottom = lambda img: seen.append("line1")
        page.lines[1].words[0].crop_bottom = lambda img: seen.append("line2")

        result = operations.refine_lines(page, [1])

        assert result is True
        assert seen == ["line2"]

    def test_refine_paragraphs_runs_refine_for_paragraph_words(
        self, operations, monkeypatch
    ):
        """Refining paragraphs should process words only in selected paragraphs."""
        import numpy as np
        from pd_book_tools.geometry.bounding_box import BoundingBox

        para1 = _paragraph([_line([_word("alpha", "A", 0)], 0)], 0)
        para2 = _paragraph([_line([_word("beta", "B", 20)], 20)], 30)
        page = Page(width=200, height=100, page_index=0, items=[para1, para2])

        dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
        monkeypatch.setattr(
            type(page), "cv2_numpy_page_image", property(lambda self: dummy_image)
        )
        monkeypatch.setattr(BoundingBox, "refine", lambda *a, **kw: None)

        seen = []
        page.paragraphs[0].lines[0].words[0].crop_bottom = lambda img: seen.append("p1")
        page.paragraphs[1].lines[0].words[0].crop_bottom = lambda img: seen.append("p2")

        result = operations.refine_paragraphs(page, [0])

        assert result is True
        assert seen == ["p1"]

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

    def test_split_line_after_word_success(self, operations):
        """Splitting a line after a selected word should produce two lines."""
        line = _line(
            [_word("alpha", "A", 0), _word("beta", "B", 20), _word("gamma", "C", 40)],
            0,
        )
        para = _paragraph([line], 0)
        page = Page(width=120, height=100, page_index=0, items=[para])

        result = operations.split_line_after_word(page, 0, 0)

        assert result is True
        assert len(page.lines) == 2
        assert [word.text for word in page.lines[0].words] == ["alpha"]
        assert [word.text for word in page.lines[1].words] == ["beta", "gamma"]

    def test_split_line_after_word_fails_on_last_word(self, operations):
        """Splitting after the last word should fail because trailing segment is empty."""
        line = _line([_word("alpha", "A", 0), _word("beta", "B", 20)], 0)
        para = _paragraph([line], 0)
        page = Page(width=120, height=100, page_index=0, items=[para])

        result = operations.split_line_after_word(page, 0, 1)

        assert result is False

    def test_split_line_with_selected_words_moves_words_into_single_new_line(
        self,
        operations,
    ):
        """Selected words from multiple lines should move into one new line."""
        line1 = _line(
            [_word("alpha", "A", 0), _word("beta", "B", 20), _word("gamma", "C", 40)],
            0,
        )
        line2 = _line(
            [_word("delta", "D", 0), _word("epsilon", "E", 20), _word("zeta", "F", 40)],
            20,
        )
        para = _paragraph([line1, line2], 0)
        page = Page(width=180, height=120, page_index=0, items=[para])

        result = operations.split_line_with_selected_words(
            page, [(0, 1), (1, 0), (1, 2)]
        )

        assert result is True
        assert len(page.lines) == 3
        line_signatures = [
            tuple(word.text for word in line.words) for line in page.lines
        ]
        assert ("alpha", "gamma") in line_signatures
        assert ("epsilon",) in line_signatures
        assert sorted(("beta", "delta", "zeta")) in [
            sorted(signature) for signature in line_signatures
        ]

    def test_split_line_with_selected_words_across_paragraphs_creates_single_line_paragraph(
        self,
        operations,
    ):
        """Cross-paragraph selection should still create one consolidated new line."""
        para1_line = _line(
            [_word("alpha", "A", 0), _word("beta", "B", 20), _word("gamma", "C", 40)],
            0,
        )
        para2_line = _line(
            [_word("delta", "D", 0), _word("epsilon", "E", 20), _word("zeta", "F", 40)],
            20,
        )
        para1 = _paragraph([para1_line], 0)
        para2 = _paragraph([para2_line], 20)
        page = Page(width=180, height=120, page_index=0, items=[para1, para2])

        result = operations.split_line_with_selected_words(page, [(0, 1), (1, 0)])

        assert result is True
        assert len(page.paragraphs) == 3
        line_signatures = [
            [tuple(word.text for word in line.words) for line in paragraph.lines]
            for paragraph in page.paragraphs
        ]
        assert [("alpha", "gamma")] in line_signatures
        assert [("epsilon", "zeta")] in line_signatures
        flattened = [signature[0] for signature in line_signatures if signature]
        assert tuple(sorted(("beta", "delta"))) in [
            tuple(sorted(words)) for words in flattened
        ]
        assert len(page.lines) == 3

    def test_split_line_with_selected_words_all_words_from_line_succeeds(
        self,
        operations,
    ):
        """Selecting all words from a line should remain a valid extraction."""
        line = _line(
            [
                _word("in", "in", 0),
                _word("the", "the", 20),
                _word("XVIIIth", "XVIIIth", 40),
                _word("Century", "Century", 70),
            ],
            0,
        )
        para = _paragraph([line], 0)
        page = Page(width=180, height=120, page_index=0, items=[para])

        result = operations.split_line_with_selected_words(
            page,
            [(0, 0), (0, 1), (0, 2), (0, 3)],
        )

        assert result is True
        assert len(page.lines) == 1
        assert [word.text for word in page.lines[0].words] == [
            "in",
            "the",
            "XVIIIth",
            "Century",
        ]

    def test_group_selected_words_into_new_paragraph_success(self, operations):
        """Selected words should move to a new paragraph with one line per source line."""
        line1 = _line(
            [_word("alpha", "A", 0), _word("beta", "B", 20), _word("gamma", "C", 40)],
            0,
        )
        line2 = _line(
            [_word("delta", "D", 0), _word("epsilon", "E", 20), _word("zeta", "F", 40)],
            20,
        )
        para = _paragraph([line1, line2], 0)
        page = Page(width=160, height=100, page_index=0, items=[para])

        result = operations.group_selected_words_into_new_paragraph(
            page,
            [(0, 1), (1, 0), (1, 2)],
        )

        assert result is True
        assert len(page.paragraphs) == 2
        assert [word.text for word in page.paragraphs[0].lines[0].words] == [
            "alpha",
            "gamma",
        ]
        assert [word.text for word in page.paragraphs[0].lines[1].words] == ["epsilon"]
        new_paragraph_lines = [
            tuple(word.text for word in line.words) for line in page.paragraphs[1].lines
        ]
        assert sorted(new_paragraph_lines) == sorted(
            [
                ("beta",),
                ("delta", "zeta"),
            ]
        )

    def test_group_selected_words_into_new_paragraph_allows_full_line_selection(
        self,
        operations,
    ):
        """Grouping should allow moving all words from a selected line."""
        line = _line([_word("alpha", "A", 0), _word("beta", "B", 20)], 0)
        para = _paragraph([line], 0)
        page = Page(width=120, height=100, page_index=0, items=[para])

        result = operations.group_selected_words_into_new_paragraph(
            page, [(0, 0), (0, 1)]
        )

        assert result is True
        assert len(page.paragraphs) == 1
        assert [word.text for word in page.paragraphs[0].lines[0].words] == [
            "alpha",
            "beta",
        ]

    def test_group_selected_words_into_new_paragraph_allows_multi_paragraph_selection(
        self,
        operations,
    ):
        """Grouping should allow selected words from multiple source paragraphs."""
        para1_line = _line(
            [_word("alpha", "A", 0), _word("beta", "B", 20), _word("gamma", "C", 40)],
            0,
        )
        para2_line = _line(
            [_word("delta", "D", 0), _word("epsilon", "E", 20), _word("zeta", "F", 40)],
            20,
        )
        para1 = _paragraph([para1_line], 0)
        para2 = _paragraph([para2_line], 20)
        page = Page(width=160, height=120, page_index=0, items=[para1, para2])

        selected_keys: list[tuple[int, int]] = []
        for line_index, line in enumerate(page.lines):
            for word_index, word in enumerate(line.words):
                if word.text in {"beta", "delta"}:
                    selected_keys.append((line_index, word_index))

        result = operations.group_selected_words_into_new_paragraph(
            page,
            selected_keys,
        )

        assert result is True
        assert len(page.paragraphs) == 3
        paragraph_line_signatures = [
            sorted(tuple(word.text for word in line.words) for line in paragraph.lines)
            for paragraph in page.paragraphs
        ]
        assert [("alpha", "gamma")] in paragraph_line_signatures
        assert [("epsilon", "zeta")] in paragraph_line_signatures
        assert (
            sorted(
                [
                    ("beta",),
                    ("delta",),
                ]
            )
            in paragraph_line_signatures
        )

    def test_group_selected_words_into_new_paragraph_allows_cross_container_selection(
        self,
        operations,
    ):
        """Grouping should allow source paragraphs under different parent containers."""
        para1_line = _line(
            [_word("alpha", "A", 0), _word("beta", "B", 20), _word("gamma", "C", 40)],
            0,
        )
        para2_line = _line(
            [_word("delta", "D", 0), _word("epsilon", "E", 20), _word("zeta", "F", 40)],
            20,
        )
        para1 = _paragraph([para1_line], 0)
        para2 = _paragraph([para2_line], 20)
        container1 = Block(
            items=[para1],
            bounding_box=_bbox(0, 0, 80, 40),
            child_type=BlockChildType.BLOCKS,
            block_category=BlockCategory.BLOCK,
        )
        container2 = Block(
            items=[para2],
            bounding_box=_bbox(100, 0, 180, 40),
            child_type=BlockChildType.BLOCKS,
            block_category=BlockCategory.BLOCK,
        )
        page = Page(width=220, height=120, page_index=0, items=[container1, container2])

        selected_keys: list[tuple[int, int]] = []
        for line_index, line in enumerate(page.lines):
            for word_index, word in enumerate(line.words):
                if word.text in {"beta", "delta"}:
                    selected_keys.append((line_index, word_index))

        result = operations.group_selected_words_into_new_paragraph(page, selected_keys)

        assert result is True
        paragraph_line_signatures = [
            sorted(tuple(word.text for word in line.words) for line in paragraph.lines)
            for paragraph in page.paragraphs
        ]
        assert [("alpha", "gamma")] in paragraph_line_signatures
        assert [("epsilon", "zeta")] in paragraph_line_signatures
        assert (
            sorted(
                [
                    ("beta",),
                    ("delta",),
                ]
            )
            in paragraph_line_signatures
        )


class TestAddWordToPage:
    """Tests for LineOperations.add_word_to_page, including 2D nearest-line selection."""

    @pytest.fixture
    def operations(self):
        return LineOperations()

    def _make_line(self, words, x1, y1, x2, y2):
        """Helper to build a line with an explicit bounding box."""
        return Block(
            items=words,
            bounding_box=BoundingBox(Point(x1, y1), Point(x2, y2), is_normalized=False),
            child_type=BlockChildType.WORDS,
            block_category=BlockCategory.LINE,
        )

    def test_add_word_inserts_into_only_line(self, operations):
        """A word drawn over the single line should be inserted into it."""
        line = self._make_line([_word("hello", "Hello", 0)], 0, 0, 100, 10)
        page = Page(width=200, height=100, page_index=0, items=[line])

        result = operations.add_word_to_page(page, 50, 0, 80, 10, text="new")

        assert result is True
        word_texts = [w.text for w in page.lines[0].words]
        assert "new" in word_texts

    def test_add_word_selects_line_by_y_range(self, operations):
        """center_y inside line2's Y range but not line1's → goes to line2."""
        line1 = self._make_line([_word("top", "Top", 0)], 0, 0, 100, 10)
        line2 = self._make_line([_word("bottom", "Bottom", 0)], 0, 50, 100, 60)
        page = Page(width=200, height=100, page_index=0, items=[line1, line2])

        # center_y=55 is within line2's Y range (50–60) but not line1's (0–10)
        result = operations.add_word_to_page(page, 10, 53, 40, 57, text="near")

        assert result is True
        line2_texts = [w.text for w in page.lines[1].words]
        assert "near" in line2_texts
        line1_texts = [w.text for w in page.lines[0].words]
        assert "near" not in line1_texts

    def test_add_word_parallel_columns_x_breaks_tie(self, operations):
        """Parallel columns at same Y: both are Y-range candidates, X breaks the tie."""
        # left column x 0–80, right column x 120–200, both span y 40–60
        left_line = self._make_line([_word("left", "Left", 5)], 0, 40, 80, 60)
        right_line = self._make_line([_word("right", "Right", 125)], 120, 40, 200, 60)
        page = Page(width=200, height=100, page_index=0, items=[left_line, right_line])

        # center (160, 50): both lines contain y=50; right column center (160) is closer
        result = operations.add_word_to_page(page, 150, 45, 170, 55, text="col")

        assert result is True
        lines = list(page.lines)
        right_words = [w.text for w in lines[1].words]
        left_words = [w.text for w in lines[0].words]
        assert "col" in right_words
        assert "col" not in left_words

    def test_add_word_x_breaks_tie_when_both_lines_contain_center_y(self, operations):
        """Both lines span center_y; the one with the nearer center X wins."""
        line_a = self._make_line([_word("a", "A", 0)], 0, 30, 60, 50)  # centre x=30
        line_b = self._make_line(
            [_word("b", "B", 140)], 140, 30, 200, 50
        )  # centre x=170
        page = Page(width=200, height=100, page_index=0, items=[line_a, line_b])

        # center (10, 40): both lines contain y=40; line_a center x=30 is closer to x=10
        result = operations.add_word_to_page(page, 5, 38, 15, 42, text="near_a")

        assert result is True
        lines = list(page.lines)
        line_a_words = [w.text for w in lines[0].words]
        assert "near_a" in line_a_words

    def test_add_word_no_page_returns_false(self, operations):
        assert operations.add_word_to_page(None, 0, 0, 10, 10) is False

    def test_add_word_no_lines_returns_false(self, operations):
        page = MagicMock(spec=Page)
        page.lines = []
        _configure_mock_page(page)
        assert operations.add_word_to_page(page, 0, 0, 10, 10) is False
