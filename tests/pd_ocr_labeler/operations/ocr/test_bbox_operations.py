"""Tests for BboxOperations selection-scoped bbox refinement/expansion methods."""

from __future__ import annotations

import numpy as np
import pytest
from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from pd_ocr_labeler.operations.ocr.bbox_operations import BboxOperations


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


class TestBboxOperations:
    @pytest.fixture
    def ops(self):
        return BboxOperations()

    def test_refine_words_runs_refine_for_selected_words(self, ops, monkeypatch):
        """Refining words runs per-word refinement for selected keys."""
        line = _line([_word("alpha", "A", 0), _word("beta", "B", 20)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])

        dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
        monkeypatch.setattr(
            type(page), "cv2_numpy_page_image", property(lambda self: dummy_image)
        )

        second_word = page.lines[0].words[1]
        seen = []
        monkeypatch.setattr(BoundingBox, "refine", lambda *a, **kw: None)
        second_word.crop_bottom = lambda img: seen.append("second")

        result = ops.refine_words(page, [(0, 1)])

        assert result is True
        assert "second" in seen

    def test_refine_words_prefers_bbox_refine(self, ops):
        """Refine prefers BoundingBox.refine over crop helpers when image exists."""
        from unittest.mock import MagicMock

        line = _line([_word("alpha", "A", 0), _word("beta", "B", 20)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])
        page.cv2_numpy_page_image = np.zeros((20, 20), dtype=np.uint8)
        word = page.lines[0].words[1]

        original_bbox = word.bounding_box
        refined_bbox = _bbox(20, 0, 35, 10)
        original_bbox.refine = MagicMock(return_value=refined_bbox)
        word.crop_bottom = MagicMock()
        word.expand_to_content = MagicMock()

        result = ops.refine_words(page, [(0, 1)])

        assert result is True
        original_bbox.refine.assert_called_once_with(
            page.cv2_numpy_page_image,
            padding_px=1,
            expand_beyond_original=False,
        )
        word.crop_bottom.assert_not_called()
        word.expand_to_content.assert_not_called()
        assert word.bounding_box.to_ltrb() == refined_bbox.to_ltrb()

    def test_expand_then_refine_words_runs_expand_before_refine(self, ops, monkeypatch):
        """Expand-then-refine calls crop_bottom fallback when refine returns None."""
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

        result = ops.expand_then_refine_words(page, [(0, 0)])

        assert result is True
        assert "crop" in seen

    def test_expand_then_refine_words_iterates_until_bbox_stabilizes(
        self, ops, monkeypatch
    ):
        """Expand-then-refine runs multiple passes until bbox no longer changes."""
        line = _line([_word("alpha", "A", 0)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])
        word = page.lines[0].words[0]

        dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
        monkeypatch.setattr(
            type(page), "cv2_numpy_page_image", property(lambda self: dummy_image)
        )

        calls = {"crop": 0}
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

        result = ops.expand_then_refine_words(page, [(0, 0)])

        assert result is True
        assert calls["crop"] >= 2
        assert page.lines[0].words[0].bounding_box.bottom_right.x == 15

    def test_expand_then_refine_words_prefers_bbox_refine_expand_mode(self, ops):
        """Expand-then-refine prefers BoundingBox.refine(expand_beyond_original=True)."""
        from unittest.mock import MagicMock

        line = _line([_word("alpha", "A", 0)], 0)
        page = Page(width=200, height=100, page_index=0, items=[line])
        page.cv2_numpy_page_image = np.zeros((20, 20), dtype=np.uint8)
        word = page.lines[0].words[0]

        original_bbox = word.bounding_box
        refined_bbox = _bbox(0, 0, 12, 10)
        original_bbox.refine = MagicMock(return_value=refined_bbox)
        word.expand_to_content = MagicMock()
        word.crop_bottom = MagicMock()

        result = ops.expand_then_refine_words(page, [(0, 0)])

        assert result is True
        original_bbox.refine.assert_called_with(
            page.cv2_numpy_page_image,
            padding_px=0,
            expand_beyond_original=True,
        )
        word.expand_to_content.assert_not_called()
        word.crop_bottom.assert_not_called()
        assert word.bounding_box.to_ltrb() == refined_bbox.to_ltrb()

    def test_refine_lines_runs_refine_for_line_words(self, ops, monkeypatch):
        """Refining lines processes all words in selected lines."""
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

        result = ops.refine_lines(page, [1])

        assert result is True
        assert seen == ["line2"]

    def test_refine_paragraphs_runs_refine_for_paragraph_words(self, ops, monkeypatch):
        """Refining paragraphs processes words only in selected paragraphs."""
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

        result = ops.refine_paragraphs(page, [0])

        assert result is True
        assert seen == ["p1"]
