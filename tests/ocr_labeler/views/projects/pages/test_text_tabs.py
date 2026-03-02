from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.state.page_state import PageState
from ocr_labeler.views.projects.pages.text_tabs import TextTabs


class _DeletedContainer:
    @property
    def client(self):
        raise RuntimeError("The client this element belongs to has been deleted.")


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


def test_text_tabs_detaches_stale_listeners_when_ui_is_disposed():
    """Disposed UI containers should unregister TextTabs listeners to avoid stale callbacks."""
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
    )

    text_tabs = TextTabs(page_state=page_state)

    assert text_tabs.model._on_page_state_change in page_state.on_change
    assert text_tabs._on_project_state_changed in project_state.on_change

    text_tabs.container = _DeletedContainer()
    text_tabs._on_project_state_changed()

    assert text_tabs._disposed is True
    assert text_tabs.model._on_page_state_change not in page_state.on_change
    assert text_tabs._on_project_state_changed not in project_state.on_change


def test_text_tabs_skips_duplicate_word_match_update_for_same_page_payload():
    """Repeated update requests with identical page payload should not recompute matches."""
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
    )

    text_tabs = TextTabs(page_state=page_state)
    text_tabs.word_match_view = MagicMock()

    page = SimpleNamespace(
        name="p001.png",
        index=0,
        blocks=[SimpleNamespace(text="line1"), SimpleNamespace(text="line2")],
    )

    text_tabs.update_word_matches(page)
    text_tabs.update_word_matches(page)

    text_tabs.word_match_view.update_from_page.assert_called_once_with(page)


def test_text_tabs_updates_when_line_payload_changes_even_if_page_object_same():
    """Line-level edits (e.g., merge) should invalidate dedupe and refresh matches."""
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        merge_lines=lambda *_: True,
    )

    text_tabs = TextTabs(page_state=page_state)
    text_tabs.word_match_view = MagicMock()

    page = SimpleNamespace(
        name="p001.png",
        index=0,
        lines=[SimpleNamespace(text="line1"), SimpleNamespace(text="line2")],
        blocks=[SimpleNamespace(text="block1")],
    )

    text_tabs.update_word_matches(page)
    page.lines = [SimpleNamespace(text="line1")]
    text_tabs.update_word_matches(page)

    assert text_tabs.word_match_view.update_from_page.call_count == 2


def test_text_tabs_merge_callback_rematches_gt_on_merged_line(tmp_path):
    """TextTabs merge callback should merge lines and rematch GT text on merged line."""
    page_state = PageState()

    line1 = _line([_word("alpha", 0)], 0)
    line2 = _line([_word("beta", 20)], 20)
    page = Page(width=100, height=100, page_index=0, items=[line1, line2])
    page.name = "page_001.png"

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

        def queue_notification(self, _message: str, _type: str = "info"):
            return None

    project = SimpleNamespace(
        pages=[page],
        image_paths=[Path("/tmp/page_001.png")],
        ground_truth_map={"page_001.png": "alpha beta"},
    )

    page_state.set_project_context(project, tmp_path, ParentStateStub())
    page_state.current_page = page
    page_state.current_page_model = page_model
    page_state._current_page_index = 0

    text_tabs = TextTabs(page_state=page_state, page_index=0)

    result = text_tabs.word_match_view.merge_lines_callback([0, 1])

    assert result is True
    assert len(page.lines) == 1
    assert page.lines[0].text == "alpha beta"
    assert page.lines[0].ground_truth_text == "alpha beta"
