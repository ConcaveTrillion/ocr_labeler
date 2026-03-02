from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.state.page_state import PageState
from ocr_labeler.viewmodels.project.page_state_view_model import PageStateViewModel
from ocr_labeler.views.projects.pages.image_tabs import ImageTabs


class _FakeImage:
    def __init__(self):
        self.source = ""


class _Marker:
    def __init__(self, value: int):
        self.value = value


def _bbox(x1: int, y1: int, x2: int, y2: int) -> BoundingBox:
    return BoundingBox(Point(x1, y1), Point(x2, y2), is_normalized=False)


def _word(text: str, x: int) -> Word:
    return Word(
        text=text,
        bounding_box=_bbox(x, 0, x + 10, 10),
        ocr_confidence=1.0,
        ground_truth_text="",
    )


def _line(words: list[Word], x: int) -> Block:
    return Block(
        items=words,
        bounding_box=_bbox(x, 0, x + 20, 10),
        child_type=BlockChildType.WORDS,
        block_category=BlockCategory.LINE,
    )


def test_image_tabs_lines_source_updates_after_merge(tmp_path, monkeypatch):
    """Merging lines should trigger image callback with updated line bbox overlay."""
    page_state = PageState()

    line1 = _line([_word("alpha", 0)], 0)
    line2 = _line([_word("beta", 20)], 20)
    page = Page(width=100, height=100, page_index=0, items=[line1, line2])
    page.name = "page_001.png"

    page.test_original = _Marker(10)
    page.test_paragraphs = _Marker(20)
    page.test_lines = _Marker(30)
    page.test_words = _Marker(40)
    page.test_mismatches = _Marker(50)

    refresh_calls = {"count": 0}

    def _refresh_page_images():
        refresh_calls["count"] += 1
        if len(page.lines) == 1:
            page.test_paragraphs = _Marker(120)
            page.test_lines = _Marker(130)
            page.test_words = _Marker(140)
            page.test_mismatches = _Marker(150)
        else:
            page.test_paragraphs = _Marker(20)
            page.test_lines = _Marker(30)
            page.test_words = _Marker(40)
            page.test_mismatches = _Marker(50)

    page.refresh_page_images = _refresh_page_images

    page_model = SimpleNamespace(
        page=page,
        page_source="ocr",
        name="page_001.png",
        image_path=None,
    )

    class ParentStateStub:
        def __init__(self):
            self.current_page_index = 0
            self.on_change = []

        def ensure_page_model(self, _index: int, force_ocr: bool = False):
            _ = force_ocr
            return page_model

    project = SimpleNamespace(
        pages=[page],
        image_paths=[Path("/tmp/page_001.png")],
        ground_truth_map={"page_001.png": "alpha beta"},
    )

    page_state.set_project_context(project, tmp_path, ParentStateStub())
    page_state.current_page = page
    page_state.current_page_model = page_model
    page_state._current_page_index = 0

    vm = PageStateViewModel(page_state)

    monkeypatch.setattr(
        vm,
        "_image_mappings",
        lambda: [
            ("original_image_source", "test_original"),
            ("paragraphs_image_source", "test_paragraphs"),
            ("lines_image_source", "test_lines"),
            ("words_image_source", "test_words"),
            ("mismatches_image_source", "test_mismatches"),
        ],
    )

    monkeypatch.setattr(
        vm,
        "_encode_image",
        lambda image: "" if image is None else f"encoded:{image.value}",
    )

    image_tabs = ImageTabs(vm)
    image_tabs.images = {
        "Original": _FakeImage(),
        "Paragraphs": _FakeImage(),
        "Lines": _FakeImage(),
        "Words": _FakeImage(),
        "Mismatches": _FakeImage(),
    }

    vm._update_image_sources_blocking()
    assert image_tabs.images["Lines"].source == "encoded:30"

    assert page_state.merge_lines(0, [0, 1]) is True

    assert refresh_calls["count"] >= 1
    assert image_tabs.images["Lines"].source == "encoded:130"
