"""Save/load round-trip tests for page persistence.

Verifies that page data survives a full save → load cycle through
``PageOperations.save_page`` → ``PageOperations.load_page_model``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.models.page_model import PageModel
from ocr_labeler.operations.ocr.page_operations import PageOperations

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _bbox(x1: int, y1: int, x2: int, y2: int) -> BoundingBox:
    return BoundingBox(Point(x1, y1), Point(x2, y2), is_normalized=False)


def _word(text: str, x: int, gt_text: str = "") -> Word:
    w = Word(
        text=text,
        bounding_box=_bbox(x, 0, x + 40, 20),
        ocr_confidence=0.95,
        ground_truth_text=gt_text,
    )
    return w


def _line(words: list[Word], y: int = 0) -> Block:
    return Block(
        items=words,
        bounding_box=_bbox(0, y, 200, y + 20),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
    )


def _paragraph(lines: list[Block], y: int = 0) -> Block:
    return Block(
        items=lines,
        bounding_box=_bbox(0, y, 200, y + 40),
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.PARAGRAPH,
    )


def _make_page(*, gt_words: bool = False, page_index: int = 0) -> Page:
    """Create a test page with two words on one line in one paragraph."""
    w1 = _word("hello", 0, gt_text="Hello" if gt_words else "")
    w2 = _word("world", 50, gt_text="World" if gt_words else "")
    line = _line([w1, w2], y=0)
    para = _paragraph([line], y=0)
    return Page(items=[para], width=200, height=100, page_index=page_index)


def _create_dummy_image(path: Path) -> None:
    """Write a minimal PNG to *path* using raw bytes."""
    # 1x1 white PNG
    import struct
    import zlib

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        raw = chunk_type + data
        return (
            struct.pack(">I", len(data))
            + raw
            + struct.pack(">I", zlib.crc32(raw) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw_data = zlib.compress(b"\x00\xff\xff\xff")
    idat = _chunk(b"IDAT", raw_data)
    iend = _chunk(b"IEND", b"")
    path.write_bytes(sig + ihdr + idat + iend)


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project directory with a dummy image."""
    project = tmp_path / "test-project"
    project.mkdir()
    img = project / "001.png"
    _create_dummy_image(img)
    return project


@pytest.fixture()
def save_dir(tmp_path: Path) -> Path:
    """Return an isolated save directory so parallel tests don't collide."""
    d = tmp_path / "saved"
    d.mkdir()
    return d


# ------------------------------------------------------------------
# Basic round-trip
# ------------------------------------------------------------------


class TestBasicRoundTrip:
    """Save a page and load it back — verify core data survives."""

    def test_word_text_preserved(self, project_dir: Path, save_dir: Path) -> None:
        page = _make_page()
        page.image_path = str(project_dir / "001.png")

        ops = PageOperations()
        model = PageModel(page=page, page_source="ocr", index=0)
        assert ops.save_page(model, project_dir, save_directory=save_dir) is True

        result = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        assert result is not None
        loaded_model, _ = result
        loaded_page = loaded_model.page

        words = list(loaded_page.lines[0].words)
        assert len(words) == 2
        assert words[0].text == "hello"
        assert words[1].text == "world"

    def test_bounding_boxes_preserved(self, project_dir: Path, save_dir: Path) -> None:
        page = _make_page()
        page.image_path = str(project_dir / "001.png")

        ops = PageOperations()
        model = PageModel(page=page, page_source="ocr", index=0)
        ops.save_page(model, project_dir, save_directory=save_dir)

        loaded_model, _ = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        loaded_page = loaded_model.page

        w = list(loaded_page.lines[0].words)[0]
        bbox = w.bounding_box
        assert float(bbox.minX) == pytest.approx(0.0)
        assert float(bbox.minY) == pytest.approx(0.0)
        assert float(bbox.maxX) == pytest.approx(40.0)
        assert float(bbox.maxY) == pytest.approx(20.0)

    def test_ground_truth_text_preserved(
        self, project_dir: Path, save_dir: Path
    ) -> None:
        page = _make_page(gt_words=True)
        page.image_path = str(project_dir / "001.png")

        ops = PageOperations()
        model = PageModel(page=page, page_source="ocr", index=0)
        ops.save_page(model, project_dir, save_directory=save_dir)

        loaded_model, _ = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        loaded_page = loaded_model.page

        words = list(loaded_page.lines[0].words)
        assert words[0].ground_truth_text == "Hello"
        assert words[1].ground_truth_text == "World"

    def test_page_dimensions_preserved(self, project_dir: Path, save_dir: Path) -> None:
        page = _make_page()
        page.image_path = str(project_dir / "001.png")

        ops = PageOperations()
        model = PageModel(page=page, page_source="ocr", index=0)
        ops.save_page(model, project_dir, save_directory=save_dir)

        loaded_model, _ = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        loaded_page = loaded_model.page

        assert loaded_page.width == 200
        assert loaded_page.height == 100

    def test_paragraph_structure_preserved(
        self, project_dir: Path, save_dir: Path
    ) -> None:
        """Paragraph→line→word hierarchy survives round-trip."""
        w1 = _word("a", 0)
        w2 = _word("b", 50)
        w3 = _word("c", 0)
        line1 = _line([w1, w2], y=0)
        line2 = _line([w3], y=30)
        para = _paragraph([line1, line2], y=0)
        page = Page(items=[para], width=200, height=100, page_index=0)
        page.image_path = str(project_dir / "001.png")

        ops = PageOperations()
        model = PageModel(page=page, page_source="ocr", index=0)
        ops.save_page(model, project_dir, save_directory=save_dir)

        loaded_model, _ = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        loaded_page = loaded_model.page

        paragraphs = list(loaded_page.paragraphs)
        assert len(paragraphs) == 1
        lines = list(paragraphs[0].lines)
        assert len(lines) == 2
        assert len(list(lines[0].words)) == 2
        assert len(list(lines[1].words)) == 1


# ------------------------------------------------------------------
# Word attributes round-trip
# ------------------------------------------------------------------


class TestWordAttributesRoundTrip:
    """Verify word-level attributes survive save/load."""

    def test_validated_word_attribute_round_trip(
        self, project_dir: Path, save_dir: Path
    ) -> None:
        page = _make_page()
        page.image_path = str(project_dir / "001.png")

        # Set validated via word_labels (the persistence mechanism)
        w = list(page.lines[0].words)[0]
        w.word_labels = list(w.word_labels) + ["validated"]

        ops = PageOperations()
        model = PageModel(page=page, page_source="ocr", index=0)
        ops.save_page(model, project_dir, save_directory=save_dir)

        loaded_model, _ = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        loaded_words = list(loaded_model.page.lines[0].words)
        # word_attributes sidecar persists validated via word_labels
        assert "validated" in list(loaded_words[0].word_labels)
        # Second word should not be validated
        assert "validated" not in list(loaded_words[1].word_labels)

    def test_style_labels_round_trip(self, project_dir: Path, save_dir: Path) -> None:
        page = _make_page()
        page.image_path = str(project_dir / "001.png")

        w = list(page.lines[0].words)[0]
        if hasattr(w, "text_style_labels"):
            w.text_style_labels = ["italics"]
            w.text_style_label_scopes = {"italics": "whole"}

        ops = PageOperations()
        model = PageModel(page=page, page_source="ocr", index=0)
        ops.save_page(model, project_dir, save_directory=save_dir)

        loaded_model, _ = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        loaded_w = list(loaded_model.page.lines[0].words)[0]
        labels = getattr(loaded_w, "text_style_labels", None)
        if labels is not None:
            assert "italics" in labels


# ------------------------------------------------------------------
# Original page round-trip
# ------------------------------------------------------------------


class TestOriginalPageRoundTrip:
    """Verify original_page is saved and restored."""

    def test_original_page_saved_and_loaded(
        self, project_dir: Path, save_dir: Path
    ) -> None:
        page = _make_page(gt_words=True)
        page.image_path = str(project_dir / "001.png")

        original = _make_page()
        original.image_path = str(project_dir / "001.png")

        ops = PageOperations()
        model = PageModel(page=page, page_source="ocr", index=0)
        ops.save_page(
            model, project_dir, save_directory=save_dir, original_page=original
        )

        loaded_model, original_dict = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        assert original_dict is not None

        restored = Page.from_dict(original_dict)
        words = list(restored.lines[0].words)
        assert words[0].text == "hello"
        assert words[1].text == "world"


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


class TestEdgeCases:
    """Edge-case save/load round-trip scenarios."""

    def test_empty_page_round_trip(self, project_dir: Path, save_dir: Path) -> None:
        page = Page(items=[], width=100, height=50, page_index=0)
        page.image_path = str(project_dir / "001.png")

        ops = PageOperations()
        model = PageModel(page=page, page_source="ocr", index=0)
        ops.save_page(model, project_dir, save_directory=save_dir)

        result = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        assert result is not None
        loaded_model, _ = result
        assert loaded_model.page.width == 100
        assert loaded_model.page.height == 50

    def test_load_nonexistent_returns_none(
        self, project_dir: Path, save_dir: Path
    ) -> None:
        ops = PageOperations()
        result = ops.load_page_model(
            page_number=99, project_root=project_dir, save_directory=save_dir
        )
        assert result is None

    def test_multiple_pages_independent(
        self, project_dir: Path, save_dir: Path
    ) -> None:
        """Save two pages with different indices, load them independently."""
        ops = PageOperations()

        page1 = _make_page(page_index=0)
        page1.image_path = str(project_dir / "001.png")
        # Create a second image
        _create_dummy_image(project_dir / "002.png")
        page2 = Page(
            items=[_paragraph([_line([_word("only", 0)])])],
            width=200,
            height=100,
            page_index=1,
        )
        page2.image_path = str(project_dir / "002.png")

        m1 = PageModel(page=page1, page_source="ocr", index=0)
        m2 = PageModel(page=page2, page_source="ocr", index=1)

        ops.save_page(m1, project_dir, save_directory=save_dir)
        ops.save_page(m2, project_dir, save_directory=save_dir)

        r1 = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        r2 = ops.load_page_model(
            page_number=2, project_root=project_dir, save_directory=save_dir
        )

        assert r1 is not None
        assert r2 is not None
        words1 = list(r1[0].page.lines[0].words)
        words2 = list(r2[0].page.lines[0].words)
        assert len(words1) == 2
        assert len(words2) == 1
        assert words1[0].text == "hello"
        assert words2[0].text == "only"

    def test_ocr_confidence_preserved(self, project_dir: Path, save_dir: Path) -> None:
        page = _make_page()
        page.image_path = str(project_dir / "001.png")

        ops = PageOperations()
        model = PageModel(page=page, page_source="ocr", index=0)
        ops.save_page(model, project_dir, save_directory=save_dir)

        loaded_model, _ = ops.load_page_model(
            page_number=1, project_root=project_dir, save_directory=save_dir
        )
        w = list(loaded_model.page.lines[0].words)[0]
        assert w.ocr_confidence == pytest.approx(0.95)
