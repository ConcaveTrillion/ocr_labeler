from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.state.page_state import PageState
from ocr_labeler.viewmodels.project import page_state_view_model as vm_module
from ocr_labeler.viewmodels.project.page_state_view_model import PageStateViewModel
from ocr_labeler.views.projects.pages.image_tabs import ImageTabs


class _FakeImage:
    def __init__(self):
        self.source = ""


class _FakeInteractiveImage:
    def __init__(self):
        self.source = ""
        self.content = ""


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


def _paragraph(lines: list[Block], y: int) -> Block:
    return Block(
        items=lines,
        bounding_box=_bbox(0, y, 180, y + 20),
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.PARAGRAPH,
    )


def test_image_tabs_source_updates_after_merge(tmp_path, monkeypatch):
    """Merging lines should trigger image callback with updated unified viewport source."""
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
        vm_module,
        "cache_image_to_disk",
        lambda img, image_type, page_index, project_id, ext, cache_dir: (
            "" if img is None else f"encoded:{img.value}"
        ),
    )

    image_tabs = ImageTabs(vm)
    image_tabs.images = {
        "Viewport": _FakeImage(),
    }

    vm._update_image_sources_blocking()
    assert image_tabs.images["Viewport"].source == "encoded:10"

    assert page_state.merge_lines(0, [0, 1]) is True

    assert refresh_calls["count"] >= 1
    assert image_tabs.images["Viewport"].source == "encoded:110"


def test_image_tabs_select_words_in_rect_returns_line_word_indices():
    page = Page(
        width=200,
        height=100,
        page_index=0,
        items=[
            _line([_word("alpha", 10), _word("beta", 60)], 10),
            _line([_word("gamma", 120)], 120),
        ],
    )

    vm = SimpleNamespace(set_image_update_callback=lambda _cb: None)
    image_tabs = ImageTabs(vm)

    selected = image_tabs._select_words_in_rect(page, 5, 0, 75, 20)

    assert selected == {(0, 0), (0, 1)}


def test_image_tabs_apply_box_selection_invokes_callback_with_selected_words():
    page = Page(
        width=100,
        height=100,
        page_index=0,
        items=[
            _line([_word("alpha", 10), _word("beta", 40)], 10),
        ],
    )

    captured = {}

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(
        _VmStub(),
        on_words_selected=lambda selection: captured.setdefault("selection", selection),
    )
    image_tabs._drag_start = (0.0, 0.0)
    image_tabs._drag_current = (35.0, 20.0)

    image_tabs._apply_box_selection()

    assert captured["selection"] == {(0, 0)}


def test_image_tabs_shift_drag_deselects_words_in_box():
    page = Page(
        width=100,
        height=100,
        page_index=0,
        items=[
            _line([_word("alpha", 10), _word("beta", 40)], 10),
        ],
    )

    captured = {}

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(
        _VmStub(),
        on_words_selected=lambda selection: captured.setdefault("selection", selection),
    )
    image_tabs.set_selected_words({(0, 0), (0, 1)})
    image_tabs._drag_start = (0.0, 0.0)
    image_tabs._drag_current = (35.0, 20.0)
    image_tabs._drag_remove_mode = True

    image_tabs._apply_box_selection()

    assert captured["selection"] == {(0, 1)}
    assert image_tabs._selected_word_indices == {(0, 1)}


def test_image_tabs_ctrl_drag_adds_words_in_box():
    page = Page(
        width=100,
        height=100,
        page_index=0,
        items=[
            _line([_word("alpha", 10), _word("beta", 40)], 10),
        ],
    )

    captured = {}

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(
        _VmStub(),
        on_words_selected=lambda selection: captured.setdefault("selection", selection),
    )
    image_tabs.set_selected_words({(0, 1)})
    image_tabs._drag_start = (0.0, 0.0)
    image_tabs._drag_current = (35.0, 20.0)
    image_tabs._drag_add_mode = True

    image_tabs._apply_box_selection()

    assert captured["selection"] == {(0, 0), (0, 1)}
    assert image_tabs._selected_word_indices == {(0, 0), (0, 1)}


def test_image_tabs_select_words_from_blocks_when_lines_missing():
    block_a = _line([_word("alpha", 10)], 10)
    block_b = _line([_word("beta", 50)], 50)
    page = SimpleNamespace(
        width=100,
        height=100,
        lines=[],
        blocks=[block_a, block_b],
    )

    vm = SimpleNamespace(set_image_update_callback=lambda _cb: None)
    image_tabs = ImageTabs(vm)

    selected = image_tabs._select_words_in_rect(page, 0, 0, 30, 20)

    assert selected == {(0, 0)}


def test_image_tabs_select_words_in_rect_applies_display_scale_for_large_pages():
    page = SimpleNamespace(
        width=2400,
        height=1200,
        lines=[
            _line([_word("alpha", 1000)], 1000),
        ],
        cv2_numpy_page_image=SimpleNamespace(shape=(1200, 2400, 3)),
    )

    vm = SimpleNamespace(set_image_update_callback=lambda _cb: None)
    image_tabs = ImageTabs(vm)

    selected = image_tabs._select_words_in_rect(page, 495, 0, 510, 10)

    assert selected == {(0, 0)}


def test_image_tabs_apply_box_selection_on_lines_selects_line_words():
    page = Page(
        width=200,
        height=100,
        page_index=0,
        items=[
            _line([_word("alpha", 10), _word("beta", 40)], 10),
            _line([_word("gamma", 120)], 120),
        ],
    )

    captured = {}

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(
        _VmStub(),
        on_words_selected=lambda selection: captured.setdefault("selection", selection),
    )
    image_tabs._drag_start = (0.0, 0.0)
    image_tabs._drag_current = (85.0, 20.0)

    image_tabs._apply_box_selection("Lines")

    assert captured["selection"] == {(0, 0), (0, 1)}


def test_image_tabs_select_paragraphs_in_rect_returns_indices():
    para1 = _paragraph([_line([_word("alpha", 10)], 10)], 0)
    para2 = _paragraph([_line([_word("beta", 10)], 10)], 30)
    page = Page(width=200, height=100, page_index=0, items=[para1, para2])

    vm = SimpleNamespace(set_image_update_callback=lambda _cb: None)
    image_tabs = ImageTabs(vm)

    selected = image_tabs._select_paragraphs_in_rect(page, 0, 0, 200, 22)

    assert selected == {0}


def test_image_tabs_apply_box_selection_on_paragraphs_invokes_callback():
    para1 = _paragraph([_line([_word("alpha", 10)], 10)], 0)
    para2 = _paragraph([_line([_word("beta", 10)], 10)], 30)
    page = Page(width=200, height=100, page_index=0, items=[para1, para2])

    captured = {}

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(
        _VmStub(),
        on_paragraphs_selected=lambda selection: captured.setdefault(
            "selection", selection
        ),
    )
    image_tabs._drag_start = (0.0, 0.0)
    image_tabs._drag_current = (200.0, 22.0)

    image_tabs._apply_box_selection("Paragraphs")

    assert captured["selection"] == {0}
    assert image_tabs._selected_paragraph_indices == {0}


def test_set_selected_paragraphs_uses_paragraph_bbox_source():
    line1 = _line([_word("alpha", 0)], 0)
    line2 = _line([_word("beta", 40)], 40)
    paragraph = _paragraph([line1, line2], 0)
    paragraph.bounding_box = _bbox(0, 0, 20, 10)
    page = Page(width=200, height=100, page_index=0, items=[paragraph])

    vm = SimpleNamespace(_page_state=SimpleNamespace(current_page=page))
    vm.set_image_update_callback = lambda _cb: None
    image_tabs = ImageTabs(vm)

    image_tabs.set_selected_paragraphs({0})

    assert image_tabs._selected_paragraph_indices == {0}
    assert len(image_tabs._selected_paragraph_boxes) == 1
    x1, y1, x2, y2 = image_tabs._selected_paragraph_boxes[0]
    assert (x1, y1, x2, y2) == (0.0, 0.0, 20.0, 10.0)


def test_image_tabs_ctrl_drag_on_lines_adds_line_words():
    page = Page(
        width=200,
        height=100,
        page_index=0,
        items=[
            _line([_word("alpha", 10), _word("beta", 40)], 10),
            _line([_word("gamma", 120)], 120),
        ],
    )

    captured = {}

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(
        _VmStub(),
        on_words_selected=lambda selection: captured.setdefault("selection", selection),
    )
    image_tabs.set_selected_words({(1, 0)})
    image_tabs._drag_start = (0.0, 0.0)
    image_tabs._drag_current = (85.0, 20.0)
    image_tabs._drag_add_mode = True

    image_tabs._apply_box_selection("Lines")

    assert captured["selection"] == {(0, 0), (0, 1), (1, 0)}


def test_image_tabs_clear_drag_state_removes_dashed_overlay():
    vm = SimpleNamespace(set_image_update_callback=lambda _cb: None)
    image_tabs = ImageTabs(vm)
    image_tabs.images = {
        "Words": _FakeInteractiveImage(),
        "Lines": _FakeInteractiveImage(),
    }
    image_tabs._drag_start = (0.0, 0.0)
    image_tabs._drag_current = (10.0, 10.0)
    image_tabs._drag_target_tab = "Words"
    image_tabs._drag_remove_mode = True

    image_tabs._clear_drag_state()

    assert image_tabs._drag_start is None
    assert image_tabs._drag_current is None
    assert image_tabs._drag_target_tab is None
    assert image_tabs._drag_remove_mode is False
    assert image_tabs._drag_add_mode is False
    assert "stroke-dasharray" not in image_tabs.images["Words"].content
    assert "stroke-dasharray" not in image_tabs.images["Lines"].content


def test_image_tabs_word_rebox_drag_emits_source_bbox_and_disables_mode():
    page = Page(
        width=100,
        height=100,
        page_index=0,
        items=[_line([_word("alpha", 10)], 10)],
    )
    captured = {}

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(
        _VmStub(),
        on_word_rebox_drawn=lambda x1, y1, x2, y2: captured.setdefault(
            "bbox", (x1, y1, x2, y2)
        ),
    )
    image_tabs.images = {
        "Words": _FakeInteractiveImage(),
    }
    image_tabs.enable_word_rebox_mode()

    image_tabs._handle_drag_mouse(
        "Words", SimpleNamespace(type="mousedown", image_x=10.0, image_y=15.0)
    )
    image_tabs._handle_drag_mouse(
        "Words", SimpleNamespace(type="mouseup", image_x=30.0, image_y=35.0)
    )

    assert captured["bbox"] == (10.0, 15.0, 30.0, 35.0)
    assert image_tabs._word_rebox_mode is False


def test_image_tabs_clear_drag_state_disables_word_rebox_mode():
    vm = SimpleNamespace(set_image_update_callback=lambda _cb: None)
    image_tabs = ImageTabs(vm)
    image_tabs._word_rebox_mode = True

    image_tabs._clear_drag_state()

    assert image_tabs._word_rebox_mode is False


def test_image_tabs_defaults_include_visible_layers_and_word_selection_mode():
    vm = SimpleNamespace(set_image_update_callback=lambda _cb: None)
    image_tabs = ImageTabs(vm)

    assert image_tabs.visible_layers == {
        "paragraphs": True,
        "lines": True,
        "words": True,
    }
    assert image_tabs.selection_mode == "word"


def test_image_tabs_selection_mode_updates_internal_target_tab():
    vm = SimpleNamespace(set_image_update_callback=lambda _cb: None)
    image_tabs = ImageTabs(vm)

    image_tabs._set_selection_mode("line")
    assert image_tabs.selection_mode == "line"
    assert image_tabs._selection_mode_tab() == "Lines"

    image_tabs._set_selection_mode("paragraph")
    assert image_tabs.selection_mode == "paragraph"
    assert image_tabs._selection_mode_tab() == "Paragraphs"

    image_tabs._set_selection_mode("invalid")
    assert image_tabs.selection_mode == "paragraph"


def test_image_tabs_layer_visibility_rerenders_viewport_overlays():
    page = Page(
        width=100,
        height=100,
        page_index=0,
        items=[_line([_word("alpha", 10)], 10)],
    )

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(_VmStub())
    image_tabs.images = {"Viewport": _FakeInteractiveImage()}
    image_tabs._selected_word_boxes = [(10.0, 0.0, 20.0, 10.0)]

    image_tabs._render_selection_overlay("Words")
    assert "#1d4ed8" in image_tabs.images["Viewport"].content

    image_tabs._set_layer_visibility("words", False)
    assert "#1d4ed8" not in image_tabs.images["Viewport"].content


def test_image_tabs_viewport_mouse_in_line_mode_selects_line_words():
    page = Page(
        width=200,
        height=100,
        page_index=0,
        items=[
            _line([_word("alpha", 10), _word("beta", 40)], 10),
            _line([_word("gamma", 120)], 120),
        ],
    )
    captured = {}

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(
        _VmStub(),
        on_words_selected=lambda selection: captured.setdefault("selection", selection),
    )
    image_tabs.images = {"Viewport": _FakeInteractiveImage()}
    image_tabs._set_selection_mode("line")

    image_tabs._handle_viewport_mouse(
        SimpleNamespace(
            type="mousedown", image_x=0.0, image_y=0.0, shift=False, ctrl=False
        )
    )
    image_tabs._handle_viewport_mouse(
        SimpleNamespace(
            type="mouseup", image_x=85.0, image_y=20.0, shift=False, ctrl=False
        )
    )

    assert captured["selection"] == {(0, 0), (0, 1)}


def test_image_tabs_viewport_mouse_in_paragraph_mode_selects_paragraphs():
    para1 = _paragraph([_line([_word("alpha", 10)], 10)], 0)
    para2 = _paragraph([_line([_word("beta", 10)], 10)], 30)
    page = Page(width=200, height=100, page_index=0, items=[para1, para2])
    captured = {}

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(
        _VmStub(),
        on_paragraphs_selected=lambda selection: captured.setdefault(
            "selection", selection
        ),
    )
    image_tabs.images = {"Viewport": _FakeInteractiveImage()}
    image_tabs._set_selection_mode("paragraph")

    image_tabs._handle_viewport_mouse(
        SimpleNamespace(
            type="mousedown", image_x=0.0, image_y=0.0, shift=False, ctrl=False
        )
    )
    image_tabs._handle_viewport_mouse(
        SimpleNamespace(
            type="mouseup", image_x=200.0, image_y=22.0, shift=False, ctrl=False
        )
    )

    assert captured["selection"] == {0}


def test_image_tabs_word_rebox_mode_overrides_viewport_selection_mode():
    page = Page(
        width=100,
        height=100,
        page_index=0,
        items=[_line([_word("alpha", 10)], 10)],
    )
    captured = {}

    class _VmStub:
        def __init__(self):
            self._page_state = SimpleNamespace(current_page=page)

        def set_image_update_callback(self, _cb):
            pass

    image_tabs = ImageTabs(
        _VmStub(),
        on_word_rebox_drawn=lambda x1, y1, x2, y2: captured.setdefault(
            "bbox", (x1, y1, x2, y2)
        ),
    )
    image_tabs.images = {"Viewport": _FakeInteractiveImage()}
    image_tabs._set_selection_mode("paragraph")
    image_tabs.enable_word_rebox_mode()

    image_tabs._handle_viewport_mouse(
        SimpleNamespace(
            type="mousedown", image_x=10.0, image_y=15.0, shift=False, ctrl=False
        )
    )
    image_tabs._handle_viewport_mouse(
        SimpleNamespace(
            type="mouseup", image_x=30.0, image_y=35.0, shift=False, ctrl=False
        )
    )

    assert captured["bbox"] == (10.0, 15.0, 30.0, 35.0)
