"""Tests for page-layer view composition."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.state.page_state import PageState
from ocr_labeler.viewmodels.project.page_state_view_model import PageStateViewModel
from ocr_labeler.views.callbacks import PageActionCallbacks
from ocr_labeler.views.projects.pages.content import ContentArea
from ocr_labeler.views.projects.pages.page_view import PageView


class TestPageView:
    """Test PageView factory behavior."""

    def test_from_project_returns_none_without_project_state(self):
        """Factory returns None when project state is unavailable."""
        project_view_model = SimpleNamespace(_project_state=None)

        page_view = PageView.from_project(project_view_model)

        assert page_view is None

    def test_from_project_builds_page_view_with_callbacks(self):
        """Factory wires page callbacks to PageView action handlers."""
        project_state = Mock()
        project_view_model = SimpleNamespace(_project_state=project_state)

        page_view = PageView.from_project(project_view_model)

        assert page_view is not None
        assert page_view.project_view_model is project_view_model
        assert page_view.page_state_view_model is not None
        assert page_view.page_action_callbacks.save_page == page_view._save_page_async
        assert page_view.page_action_callbacks.load_page == page_view._load_page_async
        assert (
            page_view.page_action_callbacks.refine_bboxes
            == page_view._refine_bboxes_async
        )
        assert (
            page_view.page_action_callbacks.expand_refine_bboxes
            == page_view._expand_refine_bboxes_async
        )
        assert page_view.page_action_callbacks.reload_ocr == page_view._reload_ocr_async


class _Marker:
    def __init__(self, value: int):
        self.value = value


class _FakeImage:
    def __init__(self):
        self.source = ""


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


def test_content_area_merge_redraws_viewport_image_source(tmp_path, monkeypatch):
    """Merging lines via TextTabs callback should refresh ImageTabs unified viewport source."""
    page_state = PageState()

    line1 = _line([_word("alpha", 0)], 0)
    line2 = _line([_word("beta", 20)], 20)
    page = Page(width=100, height=100, page_index=0, items=[line1, line2])
    page.name = "page_001.png"

    page.test_original = _Marker(10)
    page.test_original = _Marker(10)

    refresh_calls = {"count": 0}

    def _refresh_page_images():
        refresh_calls["count"] += 1
        if len(page.lines) == 1:
            page.test_original = _Marker(110)
        else:
            page.test_original = _Marker(10)

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

    vm = PageStateViewModel(page_state)
    monkeypatch.setattr(
        vm,
        "_image_mappings",
        lambda: [
            ("original_image_source", "test_original"),
        ],
    )
    monkeypatch.setattr(
        vm,
        "_cache_image_to_disk",
        lambda img, image_type, page_index, project_id, ext: (
            "" if img is None else f"encoded:{img.value}"
        ),
    )

    content = ContentArea(vm, callbacks=PageActionCallbacks())
    content.image_tabs.images = {
        "Viewport": _FakeImage(),
    }
    vm.set_image_update_callback(content.image_tabs._on_images_updated)
    vm._last_image_callback_signature = None

    vm._update_image_sources_blocking()
    assert content.image_tabs.images["Viewport"].source == "encoded:10"

    assert content.text_tabs.word_match_view.merge_lines_callback([0, 1]) is True

    assert refresh_calls["count"] >= 1
    assert content.image_tabs.images["Viewport"].source == "encoded:110"


@pytest.mark.asyncio
async def test_reload_ocr_async_forces_text_and_image_sync(monkeypatch):
    """Reload OCR should force text/image refresh even when staying on same page."""

    page = SimpleNamespace(name="page_001.png")
    project_state = SimpleNamespace(
        current_page_index=0,
        project=SimpleNamespace(pages=[page]),
    )
    project_view_model = SimpleNamespace(
        is_project_loading=False,
        current_page_index=0,
        command_reload_page_with_ocr=Mock(return_value=True),
        _project_state=project_state,
    )
    page_state_view_model = SimpleNamespace(command_refresh_images=Mock())

    page_view = PageView(project_view_model, page_state_view_model)
    page_view._sync_text_tabs = Mock()
    page_view._notify = Mock()

    @asynccontextmanager
    async def _noop_action_context(*_args, **_kwargs):
        yield

    page_view._action_context = _noop_action_context

    await page_view._reload_ocr_async()

    project_view_model.command_reload_page_with_ocr.assert_called_once()
    page_view._sync_text_tabs.assert_called_once_with(page)
    page_state_view_model.command_refresh_images.assert_called_once()
