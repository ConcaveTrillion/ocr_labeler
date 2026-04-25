"""Tests for preserving per-word GT edits across save/load round-trips."""

from unittest.mock import MagicMock

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from pd_ocr_labeler.state.page_state import PageState
from pd_ocr_labeler.state.project_state import ProjectState


def _bbox(x1: int, y1: int, x2: int, y2: int) -> BoundingBox:
    return BoundingBox(Point(x1, y1), Point(x2, y2), is_normalized=False)


def _word(text: str, x: int, gt_text: str = "") -> Word:
    return Word(
        text=text,
        bounding_box=_bbox(x, 0, x + 10, 10),
        ocr_confidence=1.0,
        ground_truth_text=gt_text,
    )


def _line(words: list[Word], y: int) -> Block:
    return Block(
        items=words,
        bounding_box=_bbox(0, y, 80, y + 10),
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


def _make_page(gt_text: str = "") -> Page:
    """Create a simple Page with two words.  Optionally set per-word GT."""
    w1 = _word("hello", 0, gt_text="Hello" if gt_text else "")
    w2 = _word("world", 20, gt_text="World" if gt_text else "")
    line = _line([w1, w2], 0)
    para = _paragraph([line], 0)
    return Page(
        items=[para],
        width=100,
        height=100,
        page_index=0,
    )


# ------------------------------------------------------------------
# _page_has_word_ground_truth
# ------------------------------------------------------------------


def test_page_has_word_ground_truth_detects_gt():
    """Helper returns True when at least one word carries GT text."""
    page = _make_page(gt_text="some")
    assert PageState._page_has_word_ground_truth(page) is True


def test_page_has_word_ground_truth_false_when_no_gt():
    """Helper returns False when no word has GT text."""
    page = _make_page(gt_text="")
    assert PageState._page_has_word_ground_truth(page) is False


def test_page_has_word_ground_truth_false_for_empty_page():
    """Helper returns False for a page with no items."""
    page = Page(items=[], width=100, height=100, page_index=0)
    assert PageState._page_has_word_ground_truth(page) is False


# ------------------------------------------------------------------
# Round-trip: saved GT edits survive load
# ------------------------------------------------------------------


def test_load_page_preserves_saved_gt_edits(monkeypatch, tmp_path):
    """When a loaded page already has per-word GT, skip bulk re-match."""
    page_state = PageState()

    page_with_gt = _make_page(gt_text="edited")

    class DummyPageModel:
        def __init__(self, page):
            self.page = page
            self.name = "page_001.png"
            self.image_path = None
            self.page_source = "filesystem"
            self.index = 0
            self.cached_image_filenames = {}

    class ProjectStub:
        def __init__(self):
            self.pages = [None]
            self.ground_truth_map = {"page_001.png": "Completely Different"}

    page_model = DummyPageModel(page_with_gt)

    # Stub page_ops.load_page_model to return our page_with_gt
    monkeypatch.setattr(
        page_state.page_ops,
        "load_page_model",
        lambda **_kw: (page_model, None),
    )

    page_state._project = ProjectStub()
    page_state._project_root = tmp_path

    # Stub _resolve_workspace_save_directory
    monkeypatch.setattr(
        page_state,
        "_resolve_workspace_save_directory",
        lambda _save_directory: tmp_path,
    )

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    success = page_state.load_page_from_file(page_index=0)

    assert success is True
    # Verify per-word GT is preserved, not overwritten by bulk matching
    loaded_page = page_state.current_page
    words = list(loaded_page.lines[0].words)
    assert words[0].ground_truth_text == "Hello"
    assert words[1].ground_truth_text == "World"


# ------------------------------------------------------------------
# Round-trip: first-time load (no saved GT) runs bulk match
# ------------------------------------------------------------------


def test_load_page_runs_bulk_match_when_no_saved_gt(monkeypatch, tmp_path):
    """When a loaded page has no per-word GT, bulk re-match runs normally."""
    page_state = PageState()

    page_no_gt = _make_page(gt_text="")

    class DummyPageModel:
        def __init__(self, page):
            self.page = page
            self.name = "page_001.png"
            self.image_path = None
            self.page_source = "filesystem"
            self.index = 0
            self.cached_image_filenames = {}

    class ProjectStub:
        def __init__(self):
            self.pages = [None]
            self.ground_truth_map = {"page_001.png": "GT text from source"}

    page_model = DummyPageModel(page_no_gt)

    monkeypatch.setattr(
        page_state.page_ops,
        "load_page_model",
        lambda **_kw: (page_model, None),
    )

    page_state._project = ProjectStub()
    page_state._project_root = tmp_path
    monkeypatch.setattr(
        page_state,
        "_resolve_workspace_save_directory",
        lambda _save_directory: tmp_path,
    )

    # Track whether add_ground_truth is called
    gt_calls = []
    original_add_gt = page_no_gt.add_ground_truth

    def tracking_add_gt(text):
        gt_calls.append(text)
        original_add_gt(text)

    monkeypatch.setattr(page_no_gt, "add_ground_truth", tracking_add_gt)

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    success = page_state.load_page_from_file(page_index=0)

    assert success is True
    # add_ground_truth should have been called
    assert len(gt_calls) == 1
    assert gt_calls[0] == "GT text from source"


# ------------------------------------------------------------------
# Explicit rematch_ground_truth resets per-word GT edits
# ------------------------------------------------------------------


def test_rematch_ground_truth_resets_edited_gt(monkeypatch):
    """Explicit rematch wipes per-word GT and re-matches from source text."""
    page_state = PageState()

    class PageStub:
        def __init__(self):
            self.name = "page_001.png"
            self.removed_gt = False
            self.added_gt = None

        def remove_ground_truth(self):
            self.removed_gt = True

        def add_ground_truth(self, text: str):
            self.added_gt = text

    class ProjectStub:
        def __init__(self):
            self.ground_truth_map = {"page_001.png": "fresh ground truth"}

    page = PageStub()
    page_state.current_page = page
    page_state._project = ProjectStub()
    monkeypatch.setattr(
        page_state,
        "_resolve_ground_truth_text",
        lambda page, page_model, page_index: "fresh ground truth",
    )

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.rematch_ground_truth()

    assert result is True
    assert page.removed_gt is True
    assert page.added_gt == "fresh ground truth"
    assert notified == ["changed"]


def test_rematch_ground_truth_returns_false_when_no_gt_available(monkeypatch):
    """Rematch returns False when no GT text can be resolved."""
    page_state = PageState()

    class PageStub:
        name = "page_001.png"

        def remove_ground_truth(self):
            pass

        def add_ground_truth(self, text: str):
            pass

    page_state.current_page = PageStub()
    monkeypatch.setattr(
        page_state,
        "_resolve_ground_truth_text",
        lambda page, page_model, page_index: "",
    )

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.rematch_ground_truth()

    assert result is False
    # notify_on_completion still triggers
    assert notified == ["changed"]


# ------------------------------------------------------------------
# _page_has_word_ground_truth: partial GT
# ------------------------------------------------------------------


def test_page_has_word_ground_truth_true_with_partial_gt():
    """Helper returns True when only one of two words carries GT text."""
    w1 = _word("hello", 0, gt_text="Hello")
    w2 = _word("world", 20, gt_text="")
    line = _line([w1, w2], 0)
    para = _paragraph([line], 0)
    page = Page(items=[para], width=100, height=100, page_index=0)
    assert PageState._page_has_word_ground_truth(page) is True


# ------------------------------------------------------------------
# rematch_ground_truth: page lacks GT methods
# ------------------------------------------------------------------


def test_rematch_ground_truth_returns_false_when_page_lacks_gt_methods(monkeypatch):
    """Rematch returns False when the page type has no GT methods."""
    page_state = PageState()

    class BarePageStub:
        """Page-like object without remove_ground_truth / add_ground_truth."""

        name = "page_001.png"

    page_state.current_page = BarePageStub()
    monkeypatch.setattr(
        page_state,
        "_resolve_ground_truth_text",
        lambda page, page_model, page_index: "some gt text",
    )

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.rematch_ground_truth()

    assert result is False
    assert notified == ["changed"]


# ------------------------------------------------------------------
# ProjectState.rematch_ground_truth delegation
# ------------------------------------------------------------------


def test_project_state_rematch_ground_truth_delegates(monkeypatch, tmp_path):
    """ProjectState.rematch_ground_truth delegates to the page state."""
    ps = ProjectState()
    fake_project = type("P", (), {})()
    fake_project.pages = [None]
    fake_project.ground_truth_map = {}
    fake_project.image_paths = []
    ps.project = fake_project
    ps.project_root = tmp_path

    page_state = ps.get_page_state(0)
    mock_rematch = MagicMock(return_value=True)
    monkeypatch.setattr(page_state, "rematch_ground_truth", mock_rematch)

    result = ps.rematch_ground_truth()

    assert result is True
    mock_rematch.assert_called_once()


# ------------------------------------------------------------------
# ProjectStateViewModel.command_rematch_gt
# ------------------------------------------------------------------


def test_command_rematch_gt_success(monkeypatch):
    """command_rematch_gt returns True when project state succeeds."""
    from pd_ocr_labeler.viewmodels.project.project_state_view_model import (
        ProjectStateViewModel,
    )

    ps = ProjectState()
    monkeypatch.setattr(ps, "rematch_ground_truth", MagicMock(return_value=True))

    vm = ProjectStateViewModel(ps)

    result = vm.command_rematch_gt()

    assert result is True
    ps.rematch_ground_truth.assert_called_once()


def test_command_rematch_gt_no_project_state(monkeypatch):
    """command_rematch_gt returns False when no project state is set."""
    from pd_ocr_labeler.viewmodels.project.project_state_view_model import (
        ProjectStateViewModel,
    )

    ps = ProjectState()
    vm = ProjectStateViewModel(ps)
    vm._project_state = None

    result = vm.command_rematch_gt()

    assert result is False
