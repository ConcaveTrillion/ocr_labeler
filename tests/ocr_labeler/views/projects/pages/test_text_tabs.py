from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.state.page_state import PageState, WordStyleChangedEvent
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
        on_word_style_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
    )

    text_tabs = TextTabs(page_state=page_state)

    assert text_tabs.model._on_page_state_change in page_state.on_change
    assert text_tabs._on_word_style_changed in page_state.on_word_style_change
    assert text_tabs._on_project_state_changed in project_state.on_change

    text_tabs.container = _DeletedContainer()
    text_tabs._on_project_state_changed()

    assert text_tabs._disposed is True
    assert text_tabs.model._on_page_state_change not in page_state.on_change
    assert text_tabs._on_word_style_changed not in page_state.on_word_style_change
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


def test_text_tabs_updates_when_ground_truth_changes_even_if_ocr_text_unchanged():
    """GT-only edits (e.g., OCR→GT copy) should invalidate dedupe and refresh matches."""
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

    line = SimpleNamespace(
        text="alpha beta",
        ground_truth_text="",
        words=[SimpleNamespace(text="alpha", ground_truth_text="")],
        unmatched_ground_truth_words=[],
    )
    page = SimpleNamespace(name="p001.png", index=0, lines=[line])

    text_tabs.update_word_matches(page)
    line.words[0].ground_truth_text = "alpha"
    line.ground_truth_text = "alpha"
    text_tabs.update_word_matches(page)

    assert text_tabs.word_match_view.update_from_page.call_count == 2


def test_text_tabs_updates_when_word_style_changes_even_if_text_unchanged():
    """Style-only edits should invalidate dedupe and refresh word matches."""
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

    word = SimpleNamespace(
        text="alpha",
        ground_truth_text="alpha",
        word_labels=[],
    )
    line = SimpleNamespace(
        text="alpha",
        ground_truth_text="alpha",
        words=[word],
        unmatched_ground_truth_words=[],
    )
    page = SimpleNamespace(name="p001.png", index=0, lines=[line])

    text_tabs.update_word_matches(page)
    word.word_labels = ["italic"]
    text_tabs.update_word_matches(page)

    assert text_tabs.word_match_view.update_from_page.call_count == 2


def test_text_tabs_updates_when_paragraph_structure_changes_even_if_lines_same():
    """Paragraph-only edits should invalidate dedupe and refresh word matches."""
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

    line1 = SimpleNamespace(text="line1", ground_truth_text="", words=[])
    line2 = SimpleNamespace(text="line2", ground_truth_text="", words=[])
    page = SimpleNamespace(
        name="p001.png",
        index=0,
        lines=[line1, line2],
        paragraphs=[SimpleNamespace(text="line1\nline2", lines=[line1, line2])],
    )

    text_tabs.update_word_matches(page)
    page.paragraphs = [
        SimpleNamespace(text="line1", lines=[line1]),
        SimpleNamespace(text="line2", lines=[line2]),
    ]
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


def test_text_tabs_delete_callback_rematches_gt_after_delete(tmp_path):
    """TextTabs delete callback should remove lines and rematch GT text."""
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
        ground_truth_map={"page_001.png": "alpha"},
    )

    page_state.set_project_context(project, tmp_path, ParentStateStub())
    page_state.current_page = page
    page_state.current_page_model = page_model
    page_state._current_page_index = 0

    text_tabs = TextTabs(page_state=page_state, page_index=0)

    result = text_tabs.word_match_view.delete_lines_callback([1])

    assert result is True
    assert len(page.lines) == 1
    assert page.lines[0].text == "alpha"
    assert page.lines[0].ground_truth_text == "alpha"


def test_text_tabs_ocr_to_gt_callback_invokes_page_state_method():
    """TextTabs should wire OCR→GT callback to page_state.copy_ocr_to_ground_truth."""
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        copy_ocr_to_ground_truth=lambda page_index, line_index: (
            calls.append((page_index, line_index)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=3)
    result = text_tabs.word_match_view.copy_ocr_to_gt_callback(7)

    assert result is True
    assert calls == [(3, 7)]


def test_text_tabs_edit_word_gt_callback_invokes_page_state_method():
    """TextTabs should wire per-word GT edit callback to PageState."""
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        update_word_ground_truth=lambda page_index, line_index, word_index, text: (
            calls.append((page_index, line_index, word_index, text)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=2)
    result = text_tabs.word_match_view.edit_word_ground_truth_callback(
        4,
        1,
        "edited-gt",
    )

    assert result is True
    assert calls == [(2, 4, 1, "edited-gt")]


def test_text_tabs_set_word_attributes_callback_invokes_page_state_method():
    """TextTabs should wire per-word attribute callback to PageState."""
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        update_word_attributes=lambda page_index, line_index, word_index, italic, small_caps, blackletter: (
            calls.append(
                (
                    page_index,
                    line_index,
                    word_index,
                    italic,
                    small_caps,
                    blackletter,
                )
            )
            or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=3)
    result = text_tabs.word_match_view.set_word_attributes_callback(
        4,
        1,
        True,
        False,
        True,
    )

    assert result is True
    assert calls == [(3, 4, 1, True, False, True)]


def test_text_tabs_word_style_event_routes_to_targeted_view_update():
    """Word style events should update only targeted word style controls in WordMatchView."""
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    page = SimpleNamespace(name="p001.png", index=0, lines=[], blocks=[])

    page_state = None

    def update_word_attributes(_page_index, _line_index, _word_index, *_flags):
        event = WordStyleChangedEvent(
            page_index=0,
            line_index=4,
            word_index=1,
            italic=False,
            small_caps=False,
            blackletter=True,
        )
        for listener in page_state.on_word_style_change:
            listener(event)
        for listener in page_state.on_change:
            listener()
        return True

    page_state = SimpleNamespace(
        on_change=[],
        on_word_style_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=page,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        update_word_attributes=update_word_attributes,
    )

    text_tabs = TextTabs(page_state=page_state, page_index=0)
    text_tabs.word_match_view.apply_word_style_change = MagicMock()
    text_tabs.word_match_view.update_from_page = MagicMock()

    result = text_tabs.word_match_view.set_word_attributes_callback(
        0,
        0,
        False,
        False,
        True,
    )
    assert result is True
    text_tabs.word_match_view.apply_word_style_change.assert_called_once_with(
        4,
        1,
        False,
        False,
        True,
    )
    text_tabs.word_match_view.update_from_page.assert_not_called()


def test_text_tabs_merge_paragraphs_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        merge_paragraphs=lambda page_index, paragraph_indices: (
            calls.append((page_index, paragraph_indices)) or True
        ),
        split_paragraph_after_line=lambda *_: False,
    )

    text_tabs = TextTabs(page_state=page_state, page_index=5)
    result = text_tabs.word_match_view.merge_paragraphs_callback([0, 2])

    assert result is True
    assert calls == [(5, [0, 2])]


def test_text_tabs_split_paragraph_after_line_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        merge_paragraphs=lambda *_: False,
        split_paragraph_after_line=lambda page_index, line_index: (
            calls.append((page_index, line_index)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=6)
    result = text_tabs.word_match_view.split_paragraph_after_line_callback(1)

    assert result is True
    assert calls == [(6, 1)]


def test_text_tabs_split_paragraph_with_selected_lines_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        merge_paragraphs=lambda *_: False,
        split_paragraph_after_line=lambda *_: False,
        split_paragraph_with_selected_lines=lambda page_index, line_indices: (
            calls.append((page_index, line_indices)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=7)
    result = text_tabs.word_match_view.split_paragraph_with_selected_lines_callback(
        [0, 2]
    )

    assert result is True
    assert calls == [(7, [0, 2])]


def test_text_tabs_delete_paragraphs_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        merge_paragraphs=lambda *_: False,
        split_paragraph_after_line=lambda *_: False,
        split_paragraph_with_selected_lines=lambda *_: False,
        delete_paragraphs=lambda page_index, paragraph_indices: (
            calls.append((page_index, paragraph_indices)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=8)
    result = text_tabs.word_match_view.delete_paragraphs_callback([1, 2])

    assert result is True
    assert calls == [(8, [1, 2])]


def test_text_tabs_delete_words_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        merge_paragraphs=lambda *_: False,
        split_paragraph_after_line=lambda *_: False,
        split_paragraph_with_selected_lines=lambda *_: False,
        delete_paragraphs=lambda *_: False,
        delete_words=lambda page_index, word_keys: (
            calls.append((page_index, word_keys)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=9)
    result = text_tabs.word_match_view.delete_words_callback([(0, 1), (2, 3)])

    assert result is True
    assert calls == [(9, [(0, 1), (2, 3)])]


def test_text_tabs_merge_word_left_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        merge_paragraphs=lambda *_: False,
        split_paragraph_after_line=lambda *_: False,
        split_paragraph_with_selected_lines=lambda *_: False,
        delete_paragraphs=lambda *_: False,
        delete_words=lambda *_: False,
        merge_word_left=lambda page_index, line_index, word_index: (
            calls.append((page_index, line_index, word_index)) or True
        ),
        merge_word_right=lambda *_: False,
    )

    text_tabs = TextTabs(page_state=page_state, page_index=10)
    result = text_tabs.word_match_view.merge_word_left_callback(2, 3)

    assert result is True
    assert calls == [(10, 2, 3)]


def test_text_tabs_merge_word_right_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        merge_paragraphs=lambda *_: False,
        split_paragraph_after_line=lambda *_: False,
        split_paragraph_with_selected_lines=lambda *_: False,
        delete_paragraphs=lambda *_: False,
        delete_words=lambda *_: False,
        merge_word_left=lambda *_: False,
        merge_word_right=lambda page_index, line_index, word_index: (
            calls.append((page_index, line_index, word_index)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=11)
    result = text_tabs.word_match_view.merge_word_right_callback(1, 0)

    assert result is True
    assert calls == [(11, 1, 0)]


def test_text_tabs_split_word_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        merge_paragraphs=lambda *_: False,
        split_paragraph_after_line=lambda *_: False,
        split_paragraph_with_selected_lines=lambda *_: False,
        delete_paragraphs=lambda *_: False,
        delete_words=lambda *_: False,
        merge_word_left=lambda *_: False,
        merge_word_right=lambda *_: False,
        split_word=lambda page_index, line_index, word_index, split_fraction: (
            calls.append((page_index, line_index, word_index, split_fraction)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=12)
    result = text_tabs.word_match_view.split_word_callback(1, 2, 0.4)

    assert result is True
    assert calls == [(12, 1, 2, 0.4)]


def test_text_tabs_rebox_word_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        merge_paragraphs=lambda *_: False,
        split_paragraph_after_line=lambda *_: False,
        split_paragraph_with_selected_lines=lambda *_: False,
        delete_paragraphs=lambda *_: False,
        delete_words=lambda *_: False,
        merge_word_left=lambda *_: False,
        merge_word_right=lambda *_: False,
        split_word=lambda *_: False,
        rebox_word=lambda page_index, line_index, word_index, x1, y1, x2, y2: (
            calls.append((page_index, line_index, word_index, x1, y1, x2, y2)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=13)
    result = text_tabs.word_match_view.rebox_word_callback(
        1,
        2,
        10.0,
        11.0,
        20.0,
        21.0,
    )

    assert result is True
    assert calls == [(13, 1, 2, 10.0, 11.0, 20.0, 21.0)]


def test_text_tabs_refine_words_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        refine_words=lambda page_index, word_keys: (
            calls.append((page_index, word_keys)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=14)
    result = text_tabs.word_match_view.refine_words_callback([(1, 2)])

    assert result is True
    assert calls == [(14, [(1, 2)])]


def test_text_tabs_refine_lines_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        refine_lines=lambda page_index, line_indices: (
            calls.append((page_index, line_indices)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=15)
    result = text_tabs.word_match_view.refine_lines_callback([1, 2])

    assert result is True
    assert calls == [(15, [1, 2])]


def test_text_tabs_refine_paragraphs_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        refine_paragraphs=lambda page_index, paragraph_indices: (
            calls.append((page_index, paragraph_indices)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=16)
    result = text_tabs.word_match_view.refine_paragraphs_callback([0])

    assert result is True
    assert calls == [(16, [0])]


def test_text_tabs_nudge_word_bbox_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        nudge_word_bbox=lambda page_index, line_index, word_index, left_delta, right_delta, top_delta, bottom_delta: (
            calls.append(
                (
                    page_index,
                    line_index,
                    word_index,
                    left_delta,
                    right_delta,
                    top_delta,
                    bottom_delta,
                )
            )
            or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=17)
    result = text_tabs.word_match_view.nudge_word_bbox_callback(
        2,
        3,
        1.0,
        -1.0,
        2.0,
        -2.0,
    )

    assert result is True
    assert calls == [(17, 2, 3, 1.0, -1.0, 2.0, -2.0)]


def test_text_tabs_expand_then_refine_words_callback_invokes_page_state_method():
    project_state = SimpleNamespace(
        on_change=[],
        project=SimpleNamespace(pages=[]),
        current_page_index=0,
    )
    calls = []
    page_state = SimpleNamespace(
        on_change=[],
        _project_state=project_state,
        current_gt_text="",
        current_ocr_text="",
        current_page=None,
        _current_page_index=0,
        copy_ground_truth_to_ocr=lambda *_: False,
        expand_then_refine_words=lambda page_index, word_keys: (
            calls.append((page_index, word_keys)) or True
        ),
    )

    text_tabs = TextTabs(page_state=page_state, page_index=18)
    result = text_tabs.word_match_view.expand_then_refine_words_callback([(1, 2)])

    assert result is True
    assert calls == [(18, [(1, 2)])]
