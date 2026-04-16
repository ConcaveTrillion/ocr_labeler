"""Tests for DocTR training dataset export operations."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.operations.export.doctr_export import (
    CLASSIFICATION_STYLE_LABELS,
    CLASSIFICATION_WORD_COMPONENTS,
    DocTRExportOperations,
    ExportStats,
    ExportStatus,
    WordFilter,
    _resolve_bbox,
    _resolve_text,
    check_page_export_status,
    page_always_valid,
    page_has_ground_truth,
    page_is_validated,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_bbox(x1: float = 0.1, y1: float = 0.2, x2: float = 0.3, y2: float = 0.4):
    return BoundingBox(top_left=Point(x1, y1), bottom_right=Point(x2, y2))


def _make_word(
    text: str = "hello",
    gt_text: str = "",
    word_labels: list[str] | None = None,
    text_style_labels: list[str] | None = None,
    word_components: list[str] | None = None,
    bbox: BoundingBox | None = None,
    gt_bbox: BoundingBox | None = None,
) -> Word:
    word = Word(
        text=text,
        bounding_box=bbox or _make_bbox(),
        ocr_confidence=0.95,
        word_labels=word_labels,
        text_style_labels=text_style_labels,
        word_components=word_components,
        ground_truth_text=gt_text,
        ground_truth_bounding_box=gt_bbox,
    )
    return word


def _make_line(words: list[Word]) -> Block:
    boxes = [w.bounding_box for w in words]
    union = BoundingBox.union(boxes) if boxes else _make_bbox()
    return Block(
        bounding_box=union,
        items=words,
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
    )


def _make_page(words: list[Word], width: int = 100, height: int = 100) -> Page:
    line = _make_line(words)
    para = Block(
        bounding_box=line.bounding_box,
        items=[line],
        block_category=BlockCategory.PARAGRAPH,
    )
    block = Block(
        bounding_box=para.bounding_box,
        items=[para],
        block_category=BlockCategory.BLOCK,
    )
    page = Page(width=width, height=height, page_index=0, items=[block])
    return page


def _make_image(width: int = 100, height: int = 100) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def _write_labeled_legacy(
    directory: Path,
    stem: str,
    page: Page,
    width: int = 100,
    height: int = 100,
) -> None:
    """Write a legacy-format labeled JSON and a matching black image."""
    from cv2 import imwrite as cv2_imwrite

    data = {
        "source_lib": "doctr-pgdp-labeled",
        "source_path": f"matched-ocr/{stem}.png",
        "pages": [page.to_dict()],
    }
    with open(directory / f"{stem}.json", "w") as f:
        json.dump(data, f)
    img = _make_image(width, height)
    cv2_imwrite(str(directory / f"{stem}.png"), img)


# ---------------------------------------------------------------------------
# Validation predicate tests
# ---------------------------------------------------------------------------


class TestValidationPredicates:
    def test_page_is_validated_true_all_words(self):
        w1 = _make_word(word_labels=["validated"])
        w2 = _make_word(text="world", word_labels=["validated"])
        page = _make_page([w1, w2])
        assert page_is_validated(page) is True

    def test_page_is_validated_single_word(self):
        word = _make_word(word_labels=["validated"])
        page = _make_page([word])
        assert page_is_validated(page) is True

    def test_page_is_validated_false_no_labels(self):
        word = _make_word(word_labels=[])
        page = _make_page([word])
        assert page_is_validated(page) is False

    def test_page_is_validated_false_partial(self):
        """If only some words are validated, the page is NOT validated."""
        w1 = _make_word(word_labels=["validated"])
        w2 = _make_word(text="world", word_labels=[])
        page = _make_page([w1, w2])
        assert page_is_validated(page) is False

    def test_page_is_validated_false_empty_page(self):
        """A page with no words is not validated."""
        page = Page(width=100, height=100, page_index=0, items=[])
        assert page_is_validated(page) is False

    def test_page_always_valid(self):
        page = _make_page([_make_word()])
        assert page_always_valid(page) is True

    def test_page_has_ground_truth_true(self):
        word = _make_word(gt_text="truth")
        page = _make_page([word])
        assert page_has_ground_truth(page) is True

    def test_page_has_ground_truth_false(self):
        word = _make_word()
        page = _make_page([word])
        assert page_has_ground_truth(page) is False


# ---------------------------------------------------------------------------
# WordFilter tests
# ---------------------------------------------------------------------------


class TestWordFilter:
    def test_empty_filter_matches_all(self):
        wf = WordFilter()
        word = _make_word()
        assert wf.matches(word) is True

    def test_style_filter_matches(self):
        wf = WordFilter(style_labels=frozenset(["italics"]))
        word = _make_word(text_style_labels=["italics"])
        assert wf.matches(word) is True

    def test_style_filter_no_match(self):
        wf = WordFilter(style_labels=frozenset(["italics"]))
        word = _make_word(text_style_labels=["bold"])
        assert wf.matches(word) is False

    def test_component_filter_matches(self):
        wf = WordFilter(word_components=frozenset(["footnote marker"]))
        word = _make_word(word_components=["footnote marker"])
        assert wf.matches(word) is True

    def test_component_filter_no_match(self):
        wf = WordFilter(word_components=frozenset(["footnote marker"]))
        word = _make_word(word_components=[])
        assert wf.matches(word) is False

    def test_combined_filter(self):
        wf = WordFilter(
            style_labels=frozenset(["italics"]),
            word_components=frozenset(["footnote marker"]),
        )
        word = _make_word(
            text_style_labels=["italics"], word_components=["footnote marker"]
        )
        assert wf.matches(word) is True

    def test_combined_filter_partial_no_match(self):
        wf = WordFilter(
            style_labels=frozenset(["italics"]),
            word_components=frozenset(["footnote marker"]),
        )
        word = _make_word(text_style_labels=["italics"], word_components=[])
        assert wf.matches(word) is False


# ---------------------------------------------------------------------------
# Text / bbox resolution helpers
# ---------------------------------------------------------------------------


class TestResolveHelpers:
    def test_resolve_text_prefers_gt(self):
        word = _make_word(text="ocr", gt_text="ground truth")
        assert _resolve_text(word) == "ground truth"

    def test_resolve_text_falls_back_to_ocr(self):
        word = _make_word(text="ocr")
        assert _resolve_text(word) == "ocr"

    def test_resolve_bbox_prefers_gt(self):
        gt_bbox = _make_bbox(0.5, 0.5, 0.9, 0.9)
        word = _make_word(gt_bbox=gt_bbox)
        assert _resolve_bbox(word) is gt_bbox

    def test_resolve_bbox_falls_back_to_ocr(self):
        word = _make_word()
        assert _resolve_bbox(word) is word.bounding_box


# ---------------------------------------------------------------------------
# ExportStats
# ---------------------------------------------------------------------------


class TestExportStats:
    def test_summary_string(self):
        stats = ExportStats(pages_scanned=10, pages_exported=8)
        text = stats.summary()
        assert "Pages scanned:       10" in text
        assert "Pages exported:      8" in text


# ---------------------------------------------------------------------------
# Full export integration tests (using tmp_path)
# ---------------------------------------------------------------------------


class TestDocTRExportStandard:
    def test_export_standard_detection_and_recognition(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create a page with validated words that have GT
        words = [
            _make_word(text="hello", gt_text="hello", word_labels=["validated"]),
            _make_word(
                text="wrld",
                gt_text="world",
                word_labels=["validated"],
                bbox=_make_bbox(0.4, 0.2, 0.6, 0.4),
            ),
        ]
        page = _make_page(words)
        _write_labeled_legacy(labeled_dir, "test_page_0", page)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        stats = exporter.export_standard()

        assert stats.pages_scanned == 1
        assert stats.pages_exported == 1
        assert stats.words_exported_detection == 2
        assert stats.words_exported_recognition == 2

        # Verify detection labels.json
        det_labels_path = output_dir / "detection" / "labels.json"
        assert det_labels_path.exists()
        with open(det_labels_path) as f:
            det_labels = json.load(f)
        assert len(det_labels) == 1
        entry = list(det_labels.values())[0]
        assert entry["img_dimensions"] == [100, 100]
        assert len(entry["polygons"]) == 2

        # Verify recognition labels.json
        rec_labels_path = output_dir / "recognition" / "labels.json"
        assert rec_labels_path.exists()
        with open(rec_labels_path) as f:
            rec_labels = json.load(f)
        assert len(rec_labels) == 2
        # GT-first: "wrld" OCR should map to "world" GT
        values = list(rec_labels.values())
        assert "hello" in values
        assert "world" in values

    def test_skips_non_validated_pages(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        words = [_make_word(text="hello", gt_text="hello")]
        page = _make_page(words)
        _write_labeled_legacy(labeled_dir, "page_0", page)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        stats = exporter.export_standard()

        assert stats.pages_scanned == 1
        assert stats.pages_exported == 0
        assert stats.pages_skipped_not_validated == 1

    def test_all_pages_mode(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        words = [_make_word(text="hello", gt_text="hello")]
        page = _make_page(words)
        _write_labeled_legacy(labeled_dir, "page_0", page)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_always_valid,
        )
        stats = exporter.export_standard()

        assert stats.pages_scanned == 1
        assert stats.pages_exported == 1

    def test_detection_only(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        words = [_make_word(text="hi", gt_text="hi", word_labels=["validated"])]
        page = _make_page(words)
        _write_labeled_legacy(labeled_dir, "page_0", page)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        stats = exporter.export_standard(detection=True, recognition=False)

        assert stats.words_exported_detection == 1
        assert stats.words_exported_recognition == 0
        assert (output_dir / "detection" / "labels.json").exists()
        assert not (output_dir / "recognition" / "labels.json").exists()

    def test_recognition_only(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        words = [_make_word(text="hi", gt_text="hi", word_labels=["validated"])]
        page = _make_page(words)
        _write_labeled_legacy(labeled_dir, "page_0", page)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        stats = exporter.export_standard(detection=False, recognition=True)

        assert stats.words_exported_detection == 0
        assert stats.words_exported_recognition == 1
        assert not (output_dir / "detection" / "labels.json").exists()
        assert (output_dir / "recognition" / "labels.json").exists()


class TestDocTRExportLabeled:
    def test_export_italic_only(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        words = [
            _make_word(
                text="italic_word",
                gt_text="italic_word",
                word_labels=["validated"],
                text_style_labels=["italics"],
            ),
            _make_word(
                text="regular_word",
                gt_text="regular_word",
                word_labels=["validated"],
                text_style_labels=["regular"],
                bbox=_make_bbox(0.5, 0.2, 0.7, 0.4),
            ),
        ]
        page = _make_page(words)
        _write_labeled_legacy(labeled_dir, "page_0", page)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        stats = exporter.export_labeled(style_labels=["italics"])

        # Only the italic word should be exported
        assert stats.words_exported_detection == 1
        assert stats.words_exported_recognition == 1

        with open(output_dir / "recognition" / "labels.json") as f:
            rec = json.load(f)
        assert "italic_word" in list(rec.values())
        assert "regular_word" not in list(rec.values())

    def test_export_small_caps_only(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        words = [
            _make_word(
                text="SMALL",
                gt_text="SMALL",
                word_labels=["validated"],
                text_style_labels=["small caps"],
            ),
            _make_word(
                text="REGULAR",
                gt_text="REGULAR",
                word_labels=["validated"],
                bbox=_make_bbox(0.5, 0.2, 0.7, 0.4),
            ),
        ]
        page = _make_page(words)
        _write_labeled_legacy(labeled_dir, "page_0", page)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        stats = exporter.export_labeled(style_labels=["small caps"])

        assert stats.words_exported_recognition == 1
        with open(output_dir / "recognition" / "labels.json") as f:
            rec = json.load(f)
        assert "SMALL" in list(rec.values())


class TestDocTRExportClassification:
    def test_classification_output_format(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        words = [
            _make_word(
                text="italic_word",
                gt_text="italic_word",
                word_labels=["validated"],
                text_style_labels=["italics"],
            ),
        ]
        page = _make_page(words)
        _write_labeled_legacy(labeled_dir, "page_0", page)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        stats = exporter.export_classification()

        assert stats.words_exported_recognition == 1

        with open(output_dir / "recognition" / "labels.json") as f:
            rec = json.load(f)
        entry = list(rec.values())[0]
        assert isinstance(entry, dict)
        assert entry["text"] == "italic_word"
        assert entry["labels"]["italics"] is True
        assert entry["labels"]["small caps"] is False
        # Check all classification labels are present
        for label in CLASSIFICATION_STYLE_LABELS:
            assert label in entry["labels"]
        for comp in CLASSIFICATION_WORD_COMPONENTS:
            assert comp in entry["labels"]


class TestDocTRExportEnvelopeFormat:
    def test_loads_envelope_format(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        # Word has word_labels=["validated"] persisted in the page dict —
        # no legacy word_attributes mapping required.
        word = _make_word(text="hello", gt_text="hello", word_labels=["validated"])
        page = _make_page([word])

        # Write envelope-format JSON
        envelope = {
            "schema": {"name": "ocr_labeler.user_page", "version": "2.1"},
            "provenance": {
                "saved_at": "2025-01-01T00:00:00Z",
                "saved_by": "Save Page",
            },
            "source": {
                "project_id": "test",
                "page_index": 0,
                "page_number": 1,
                "image_path": "test_page.png",
            },
            "payload": {
                "page": page.to_dict(),
            },
        }

        with open(labeled_dir / "test_page.json", "w") as f:
            json.dump(envelope, f)

        from cv2 import imwrite as cv2_imwrite

        cv2_imwrite(str(labeled_dir / "test_page.png"), _make_image())

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        stats = exporter.export_standard()

        assert stats.pages_exported == 1
        assert stats.words_exported_detection == 1


class TestDocTRExportEdgeCases:
    def test_empty_directory(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
        )
        stats = exporter.export_standard()
        assert stats.pages_scanned == 0
        assert stats.pages_exported == 0

    def test_missing_image(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        words = [_make_word(text="hi", gt_text="hi", word_labels=["validated"])]
        page = _make_page(words)
        # Write JSON but NO image
        data = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "test.png",
            "pages": [page.to_dict()],
        }
        with open(labeled_dir / "test_page.json", "w") as f:
            json.dump(data, f)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        stats = exporter.export_standard()
        assert stats.pages_skipped_no_image == 1

    def test_word_with_no_gt_text_uses_ocr_text(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        words = [_make_word(text="ocr_only", word_labels=["validated"])]
        page = _make_page(words)
        _write_labeled_legacy(labeled_dir, "page_0", page)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        stats = exporter.export_standard()
        assert stats.words_exported_recognition == 1

        with open(output_dir / "recognition" / "labels.json") as f:
            rec = json.load(f)
        assert "ocr_only" in list(rec.values())

    def test_prefix_applied(self, tmp_path):
        labeled_dir = tmp_path / "labeled"
        labeled_dir.mkdir()
        output_dir = tmp_path / "output"

        words = [_make_word(text="hi", gt_text="hi", word_labels=["validated"])]
        page = _make_page(words)
        _write_labeled_legacy(labeled_dir, "page_0", page)

        exporter = DocTRExportOperations(
            labeled_data_dir=labeled_dir,
            output_dir=output_dir,
            validation_predicate=page_is_validated,
        )
        exporter.export_standard(prefix="mybook")

        with open(output_dir / "detection" / "labels.json") as f:
            det = json.load(f)
        key = list(det.keys())[0]
        assert key.startswith("mybook_")


# ---------------------------------------------------------------------------
# Export status checks
# ---------------------------------------------------------------------------


class TestCheckPageExportStatus:
    """Tests for check_page_export_status()."""

    def test_not_exported_when_no_file(self, tmp_path):
        result = check_page_export_status(tmp_path, "proj", 0)
        assert result == ExportStatus.NOT_EXPORTED

    def test_exported_when_image_exists(self, tmp_path):
        img_dir = tmp_path / "detection" / "images"
        img_dir.mkdir(parents=True)
        (img_dir / "proj_0.png").write_bytes(b"fake")

        result = check_page_export_status(tmp_path, "proj", 0)
        assert result == ExportStatus.EXPORTED

    def test_exported_when_no_saved_json(self, tmp_path):
        img_dir = tmp_path / "detection" / "images"
        img_dir.mkdir(parents=True)
        (img_dir / "proj_0.png").write_bytes(b"fake")

        result = check_page_export_status(
            tmp_path, "proj", 0, saved_json_path=tmp_path / "nonexistent.json"
        )
        assert result == ExportStatus.EXPORTED

    def test_stale_when_saved_json_newer(self, tmp_path):
        import time

        img_dir = tmp_path / "detection" / "images"
        img_dir.mkdir(parents=True)
        img_file = img_dir / "proj_0.png"
        img_file.write_bytes(b"fake")

        # Ensure the saved JSON has a strictly newer mtime
        time.sleep(0.05)
        saved_json = tmp_path / "saved.json"
        saved_json.write_text("{}")

        result = check_page_export_status(
            tmp_path, "proj", 0, saved_json_path=saved_json
        )
        assert result == ExportStatus.STALE

    def test_exported_when_saved_json_older(self, tmp_path):
        import time

        saved_json = tmp_path / "saved.json"
        saved_json.write_text("{}")

        # Ensure the export image has a strictly newer mtime
        time.sleep(0.05)
        img_dir = tmp_path / "detection" / "images"
        img_dir.mkdir(parents=True)
        img_file = img_dir / "proj_0.png"
        img_file.write_bytes(b"fake")

        result = check_page_export_status(
            tmp_path, "proj", 0, saved_json_path=saved_json
        )
        assert result == ExportStatus.EXPORTED
