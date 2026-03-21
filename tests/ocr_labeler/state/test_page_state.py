from pathlib import Path
from types import SimpleNamespace

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.operations.persistence.persistence_paths_operations import (
    PersistencePathsOperations,
)
from ocr_labeler.state.page_state import (
    PageState,
    WordGroundTruthChangedEvent,
    WordStyleChangedEvent,
)


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
        bounding_box=_bbox(0, y, 80, y + 20),
        child_type=BlockChildType.BLOCKS,
        block_category=BlockCategory.PARAGRAPH,
    )


def test_project_state_change_refreshes_loading_cache_when_page_finishes_loading(
    tmp_path,
):
    """Ensure Loading... placeholders are replaced after async load completion."""
    page_state = PageState()

    class ParentStateStub:
        def __init__(self):
            self.current_page_index = 0
            self.on_change = []
            self._project = None

        def ensure_page_model(self, index: int, force_ocr: bool = False):
            _ = force_ocr
            page = self._project.pages[index]
            if page is None:
                return None

            class _PageModelStub:
                def __init__(self, raw_page):
                    self.page = raw_page
                    self.page_source = "ocr"

            return _PageModelStub(page)

    class ProjectStub:
        def __init__(self):
            self.pages = [None, None]
            self.ground_truth_map = {"page_002.png": "ground truth text"}

    class LoadedPageStub:
        def __init__(self, text: str, name: str):
            self.text = text
            self.name = name

    parent_state = ParentStateStub()
    project = ProjectStub()
    parent_state._project = project

    page_state.set_project_context(project, tmp_path, parent_state)
    on_change_callback = parent_state.on_change[0]

    parent_state.current_page_index = 1
    on_change_callback()
    assert page_state.current_ocr_text == "Loading..."
    assert page_state.current_gt_text == "Loading..."

    project.pages[1] = LoadedPageStub(text="ocr text", name="page_002.png")
    on_change_callback()

    assert page_state.current_ocr_text == "ocr text"
    assert page_state.current_gt_text == "ground truth text"


def test_merge_lines_reapplies_ground_truth_after_merge(monkeypatch):
    """Successful line merge should re-run page GT matching to keep word GT aligned."""
    page_state = PageState()

    class ProjectStub:
        def __init__(self):
            self.ground_truth_map = {"page_001.png": "ground truth content"}

    class PageStub:
        def __init__(self):
            self.name = "page_001.png"
            self.removed_gt = False
            self.added_gt = None
            self.overlay_refresh_called = False

        def remove_ground_truth(self):
            self.removed_gt = True

        def add_ground_truth(self, text: str):
            self.added_gt = text

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "merge_lines",
        lambda _self, _page, _line_indices: True,
    )

    page = PageStub()
    page_state.current_page = page
    page_state._project = ProjectStub()
    page_state.find_ground_truth_text = lambda page_name, gt_map: gt_map.get(page_name)

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.merge_lines(0, [0, 1])

    assert result is True
    assert page.removed_gt is True
    assert page.added_gt == "ground truth content"
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_get_page_texts_falls_back_to_project_image_path_for_gt_lookup(tmp_path):
    """GT lookup should still work when loaded page/model names are missing."""
    page_state = PageState()

    class PageStub:
        text = "ocr text"
        name = None
        image_path = None

    class PageModelStub:
        def __init__(self):
            self.page = PageStub()
            self.name = None
            self.image_path = None
            self.page_source = "ocr"

    class ParentStateStub:
        def __init__(self):
            self.current_page_index = 0
            self.on_change = []

        def ensure_page_model(self, _index: int, force_ocr: bool = False):
            _ = force_ocr
            return PageModelStub()

    class ProjectStub:
        def __init__(self):
            self.pages = [PageStub()]
            self.image_paths = [Path("/tmp/page_001.png")]
            self.ground_truth_map = {"page_001.png": "ground truth text"}

    page_state.set_project_context(ProjectStub(), tmp_path, ParentStateStub())

    ocr_text, gt_text = page_state.get_page_texts(0)

    assert ocr_text == "ocr text"
    assert gt_text == "ground truth text"


def test_merge_lines_reapplies_gt_via_project_image_path_when_page_name_missing(
    monkeypatch,
):
    """Merge rematch should work even when current page has no name attribute value."""
    page_state = PageState()

    class ProjectStub:
        def __init__(self):
            self.ground_truth_map = {"page_001.png": "ground truth content"}
            self.image_paths = [Path("/tmp/page_001.png")]

    class PageStub:
        def __init__(self):
            self.name = None
            self.removed_gt = False
            self.added_gt = None

        def remove_ground_truth(self):
            self.removed_gt = True

        def add_ground_truth(self, text: str):
            self.added_gt = text

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "merge_lines",
        lambda _self, _page, _line_indices: True,
    )

    page_state.current_page = PageStub()
    page_state.current_page_model = type(
        "PageModelStub",
        (),
        {"name": None, "image_path": None},
    )()
    page_state._project = ProjectStub()
    page_state._current_page_index = 0

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.merge_lines(0, [0, 1])

    assert result is True
    assert page_state.current_page.removed_gt is True
    assert page_state.current_page.added_gt == "ground truth content"
    assert notified == ["changed"]


def test_merge_lines_rematches_ground_truth_on_merged_line():
    """After merging lines, GT matching should rerun and annotate merged line text."""
    page_state = PageState()

    line1 = _line([_word("alpha", 0)], 0)
    line2 = _line([_word("beta", 20)], 20)
    page = Page(width=100, height=100, page_index=0, items=[line1, line2])
    page.name = "page_001.png"

    page_state.current_page = page
    page_state.current_page_model = type(
        "PageModelStub",
        (),
        {"name": "page_001.png", "image_path": None},
    )()
    page_state._project = type(
        "ProjectStub",
        (),
        {
            "ground_truth_map": {"page_001.png": "alpha beta"},
            "image_paths": [Path("/tmp/page_001.png")],
        },
    )()
    page_state._current_page_index = 0

    assert page_state.merge_lines(0, [0, 1]) is True
    assert len(page.lines) == 1
    assert page.lines[0].text == "alpha beta"
    assert page.lines[0].ground_truth_text == "alpha beta"


def test_delete_lines_reapplies_ground_truth_after_delete(monkeypatch):
    """Successful line deletion should re-run page GT matching to keep alignment stable."""
    page_state = PageState()

    class ProjectStub:
        def __init__(self):
            self.ground_truth_map = {"page_001.png": "ground truth content"}

    class PageStub:
        def __init__(self):
            self.name = "page_001.png"
            self.removed_gt = False
            self.added_gt = None
            self.overlay_refresh_called = False

        def remove_ground_truth(self):
            self.removed_gt = True

        def add_ground_truth(self, text: str):
            self.added_gt = text

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "delete_lines",
        lambda _self, _page, _line_indices: True,
    )

    page = PageStub()
    page_state.current_page = page
    page_state._project = ProjectStub()
    page_state.find_ground_truth_text = lambda page_name, gt_map: gt_map.get(page_name)

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.delete_lines(0, [1])

    assert result is True
    assert page.removed_gt is True
    assert page.added_gt == "ground truth content"
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_merge_paragraphs_rematches_ground_truth_on_merged_paragraph():
    """After merging paragraphs, GT matching should rerun and keep alignment."""
    page_state = PageState()

    para1 = _paragraph([_line([_word("alpha", 0)], 0)], 0)
    para2 = _paragraph([_line([_word("beta", 20)], 20)], 30)
    page = Page(width=100, height=100, page_index=0, items=[para1, para2])
    page.name = "page_001.png"

    page_state.current_page = page
    page_state.current_page_model = type(
        "PageModelStub",
        (),
        {"name": "page_001.png", "image_path": None},
    )()
    page_state._project = type(
        "ProjectStub",
        (),
        {
            "ground_truth_map": {"page_001.png": "alpha\n\nbeta"},
            "image_paths": [Path("/tmp/page_001.png")],
        },
    )()
    page_state._current_page_index = 0

    assert page_state.merge_paragraphs(0, [0, 1]) is True
    assert len(page.paragraphs) == 1
    assert page.paragraphs[0].text == "alpha\nbeta"


def test_delete_paragraphs_reapplies_ground_truth_after_delete(monkeypatch):
    """Successful paragraph deletion should re-run GT matching and refresh overlays."""
    page_state = PageState()

    class ProjectStub:
        def __init__(self):
            self.ground_truth_map = {"page_001.png": "ground truth content"}

    class PageStub:
        def __init__(self):
            self.name = "page_001.png"
            self.removed_gt = False
            self.added_gt = None
            self.overlay_refresh_called = False

        def remove_ground_truth(self):
            self.removed_gt = True

        def add_ground_truth(self, text: str):
            self.added_gt = text

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "delete_paragraphs",
        lambda _self, _page, _paragraph_indices: True,
    )

    page = PageStub()
    page_state.current_page = page
    page_state._project = ProjectStub()
    page_state.find_ground_truth_text = lambda page_name, gt_map: gt_map.get(page_name)

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.delete_paragraphs(0, [0])

    assert result is True
    assert page.removed_gt is True
    assert page.added_gt == "ground truth content"
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_delete_words_reapplies_ground_truth_after_delete(monkeypatch):
    """Successful word deletion should re-run GT matching and refresh overlays."""
    page_state = PageState()

    class ProjectStub:
        def __init__(self):
            self.ground_truth_map = {"page_001.png": "ground truth content"}

    class PageStub:
        def __init__(self):
            self.name = "page_001.png"
            self.removed_gt = False
            self.added_gt = None
            self.overlay_refresh_called = False

        def remove_ground_truth(self):
            self.removed_gt = True

        def add_ground_truth(self, text: str):
            self.added_gt = text

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "delete_words",
        lambda _self, _page, _word_keys: True,
    )

    page = PageStub()
    page_state.current_page = page
    page_state._project = ProjectStub()
    page_state.find_ground_truth_text = lambda page_name, gt_map: gt_map.get(page_name)

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.delete_words(0, [(0, 1)])

    assert result is True
    assert page.removed_gt is True
    assert page.added_gt == "ground truth content"
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_merge_word_left_reapplies_ground_truth_after_merge(monkeypatch):
    """Successful word merge-left should re-run GT matching and refresh overlays."""
    page_state = PageState()

    class ProjectStub:
        def __init__(self):
            self.ground_truth_map = {"page_001.png": "ground truth content"}

    class PageStub:
        def __init__(self):
            self.name = "page_001.png"
            self.removed_gt = False
            self.added_gt = None
            self.overlay_refresh_called = False

        def remove_ground_truth(self):
            self.removed_gt = True

        def add_ground_truth(self, text: str):
            self.added_gt = text

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "merge_word_left",
        lambda _self, _page, _line_index, _word_index: True,
    )

    page = PageStub()
    page_state.current_page = page
    page_state._project = ProjectStub()
    page_state.find_ground_truth_text = lambda page_name, gt_map: gt_map.get(page_name)

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.merge_word_left(0, 0, 1)

    assert result is True
    assert page.removed_gt is True
    assert page.added_gt == "ground truth content"
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_merge_word_right_reapplies_ground_truth_after_merge(monkeypatch):
    """Successful word merge-right should re-run GT matching and refresh overlays."""
    page_state = PageState()

    class ProjectStub:
        def __init__(self):
            self.ground_truth_map = {"page_001.png": "ground truth content"}

    class PageStub:
        def __init__(self):
            self.name = "page_001.png"
            self.removed_gt = False
            self.added_gt = None
            self.overlay_refresh_called = False

        def remove_ground_truth(self):
            self.removed_gt = True

        def add_ground_truth(self, text: str):
            self.added_gt = text

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "merge_word_right",
        lambda _self, _page, _line_index, _word_index: True,
    )

    page = PageStub()
    page_state.current_page = page
    page_state._project = ProjectStub()
    page_state.find_ground_truth_text = lambda page_name, gt_map: gt_map.get(page_name)

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.merge_word_right(0, 0, 0)

    assert result is True
    assert page.removed_gt is True
    assert page.added_gt == "ground truth content"
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_split_word_reapplies_ground_truth_after_split(monkeypatch):
    """Successful word split should re-run GT matching and refresh overlays."""
    page_state = PageState()

    class ProjectStub:
        def __init__(self):
            self.ground_truth_map = {"page_001.png": "ground truth content"}

    class PageStub:
        def __init__(self):
            self.name = "page_001.png"
            self.removed_gt = False
            self.added_gt = None
            self.overlay_refresh_called = False

        def remove_ground_truth(self):
            self.removed_gt = True

        def add_ground_truth(self, text: str):
            self.added_gt = text

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "split_word",
        lambda _self, _page, _line_index, _word_index, _split_fraction: True,
    )

    page = PageStub()
    page_state.current_page = page
    page_state._project = ProjectStub()
    page_state.find_ground_truth_text = lambda page_name, gt_map: gt_map.get(page_name)

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.split_word(0, 0, 0, 0.5)

    assert result is True
    assert page.removed_gt is True
    assert page.added_gt == "ground truth content"
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_split_word_vertical_closest_line_reapplies_ground_truth(monkeypatch):
    """Vertical split should re-run GT matching and refresh overlays."""
    page_state = PageState()

    class ProjectStub:
        def __init__(self):
            self.ground_truth_map = {"page_001.png": "ground truth content"}

    class PageStub:
        def __init__(self):
            self.name = "page_001.png"
            self.removed_gt = False
            self.added_gt = None
            self.overlay_refresh_called = False

        def remove_ground_truth(self):
            self.removed_gt = True

        def add_ground_truth(self, text: str):
            self.added_gt = text

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "split_word_vertically_and_assign_to_closest_line",
        lambda _self, _page, _line_index, _word_index, _split_fraction: True,
    )

    page = PageStub()
    page_state.current_page = page
    page_state._project = ProjectStub()
    page_state.find_ground_truth_text = lambda page_name, gt_map: gt_map.get(page_name)

    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.split_word_vertically_and_assign_to_closest_line(0, 0, 0, 0.5)

    assert result is True
    assert page.removed_gt is True
    assert page.added_gt == "ground truth content"
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_rebox_word_refreshes_overlay_and_notifies(monkeypatch):
    """Successful word rebox should refresh overlays and notify listeners."""
    page_state = PageState()

    class PageStub:
        def __init__(self):
            self.overlay_refresh_called = False

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "rebox_word",
        lambda _self, _page, _line_index, _word_index, _x1, _y1, _x2, _y2: True,
    )

    page = PageStub()
    page_state.current_page = page
    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.rebox_word(0, 0, 1, 10.0, 11.0, 20.0, 21.0)

    assert result is True
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_rebox_word_invalidates_overlay_cache_before_refresh(monkeypatch):
    """Rebox should clear overlay caches so refresh regenerates updated bboxes."""
    page_state = PageState()

    class PageStub:
        def __init__(self):
            self.overlay_refresh_called = False
            self.cv2_numpy_page_image_paragraph_with_bboxes = "stale-p"
            self.cv2_numpy_page_image_line_with_bboxes = "stale-l"
            self.cv2_numpy_page_image_word_with_bboxes = "stale-w"
            self.cv2_numpy_page_image_matched_word_with_colors = "stale-m"

        def refresh_page_images(self):
            self.overlay_refresh_called = True
            if (
                self.cv2_numpy_page_image_paragraph_with_bboxes is None
                and self.cv2_numpy_page_image_line_with_bboxes is None
                and self.cv2_numpy_page_image_word_with_bboxes is None
                and self.cv2_numpy_page_image_matched_word_with_colors is None
            ):
                self.cv2_numpy_page_image_word_with_bboxes = "fresh-word-overlay"

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "rebox_word",
        lambda _self, _page, _line_index, _word_index, _x1, _y1, _x2, _y2: True,
    )

    page = PageStub()
    page_state.current_page = page

    result = page_state.rebox_word(0, 0, 1, 10.0, 11.0, 20.0, 21.0)

    assert result is True
    assert page.overlay_refresh_called is True
    assert page.cv2_numpy_page_image_word_with_bboxes == "fresh-word-overlay"


def test_nudge_word_bbox_refreshes_overlay_and_notifies(monkeypatch):
    """Successful word bbox nudge should refresh overlays and notify listeners."""
    page_state = PageState()

    class PageStub:
        def __init__(self):
            self.overlay_refresh_called = False

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "nudge_word_bbox",
        lambda _self, _page, _line_index, _word_index, _left, _right, _top, _bottom, refine_after=True: (
            True
        ),
    )

    page = PageStub()
    page_state.current_page = page
    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.nudge_word_bbox(0, 0, 1, 1.0, 1.0, -1.0, -1.0)

    assert result is True
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_refine_words_refreshes_overlay_and_notifies(monkeypatch):
    """Successful word refine should refresh overlays and notify listeners."""
    page_state = PageState()

    class PageStub:
        def __init__(self):
            self.overlay_refresh_called = False

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "refine_words",
        lambda _self, _page, _word_keys: True,
    )

    page = PageStub()
    page_state.current_page = page
    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.refine_words(0, [(0, 1)])

    assert result is True
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_expand_then_refine_words_refreshes_overlay_and_notifies(monkeypatch):
    """Successful expand-then-refine should refresh overlays and notify listeners."""
    page_state = PageState()

    class PageStub:
        def __init__(self):
            self.overlay_refresh_called = False

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "expand_then_refine_words",
        lambda _self, _page, _word_keys: True,
    )

    page = PageStub()
    page_state.current_page = page
    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.expand_then_refine_words(0, [(0, 1)])

    assert result is True
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_refine_lines_refreshes_overlay_and_notifies(monkeypatch):
    """Successful line refine should refresh overlays and notify listeners."""
    page_state = PageState()

    class PageStub:
        def __init__(self):
            self.overlay_refresh_called = False

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "refine_lines",
        lambda _self, _page, _line_indices: True,
    )

    page = PageStub()
    page_state.current_page = page
    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.refine_lines(0, [0])

    assert result is True
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_refine_paragraphs_refreshes_overlay_and_notifies(monkeypatch):
    """Successful paragraph refine should refresh overlays and notify listeners."""
    page_state = PageState()

    class PageStub:
        def __init__(self):
            self.overlay_refresh_called = False

        def refresh_page_images(self):
            self.overlay_refresh_called = True

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "refine_paragraphs",
        lambda _self, _page, _paragraph_indices: True,
    )

    page = PageStub()
    page_state.current_page = page
    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.refine_paragraphs(0, [0])

    assert result is True
    assert page.overlay_refresh_called is True
    assert notified == ["changed"]


def test_update_word_ground_truth_notifies_on_success(monkeypatch):
    """Successful per-word GT edit should notify listeners for UI refresh."""
    page_state = PageState()

    class PageStub:
        pass

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "update_word_ground_truth",
        lambda _self, _page, _line_index, _word_index, _text: True,
    )

    page_state.current_page = PageStub()
    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.update_word_ground_truth(0, 1, 2, "edited")

    assert result is True
    assert notified == ["changed"]


def test_update_word_ground_truth_emits_typed_event_on_success(monkeypatch):
    """Successful per-word GT edit should emit a targeted GT change event."""
    page_state = PageState()

    class PageStub:
        pass

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "update_word_ground_truth",
        lambda _self, _page, _line_index, _word_index, _text: True,
    )

    page_state.current_page = PageStub()
    seen: list[WordGroundTruthChangedEvent] = []
    page_state.on_word_ground_truth_change.subscribe(lambda event: seen.append(event))

    result = page_state.update_word_ground_truth(4, 3, 2, "edited")

    assert result is True
    assert seen == [
        WordGroundTruthChangedEvent(
            page_index=4,
            line_index=3,
            word_index=2,
            ground_truth_text="edited",
        )
    ]


def test_update_word_attributes_notifies_on_success(monkeypatch):
    """Successful per-word attribute edit should notify listeners for UI refresh."""
    page_state = PageState()

    class PageStub:
        pass

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "update_word_attributes",
        lambda _self, _page, _line, _word, _italic, _small_caps, _blackletter, _left_footnote, _right_footnote: (
            True
        ),
    )

    page_state.current_page = PageStub()
    notified = []
    page_state.on_change = [lambda: notified.append("changed")]

    result = page_state.update_word_attributes(0, 1, 2, True, False, True, False, False)

    assert result is True
    assert notified == ["changed"]


def test_update_word_attributes_emits_typed_style_event_on_success(monkeypatch):
    """Successful word attribute edits should emit a targeted style change event."""
    page_state = PageState()

    class PageStub:
        pass

    from ocr_labeler.operations.ocr import line_operations as line_ops_module

    monkeypatch.setattr(
        line_ops_module.LineOperations,
        "update_word_attributes",
        lambda _self, _page, _line, _word, _italic, _small_caps, _blackletter, _left_footnote, _right_footnote: (
            True
        ),
    )

    page_state.current_page = PageStub()
    seen: list[WordStyleChangedEvent] = []
    page_state.on_word_style_change.subscribe(lambda event: seen.append(event))

    result = page_state.update_word_attributes(3, 1, 2, True, False, True, False, False)

    assert result is True
    assert seen == [
        WordStyleChangedEvent(
            page_index=3,
            line_index=1,
            word_index=2,
            italic=True,
            small_caps=False,
            blackletter=True,
            left_footnote=False,
            right_footnote=False,
        )
    ]


def test_split_paragraph_after_line_splits_containing_paragraph_at_line():
    """Splitting after a selected line should split that line's paragraph in two."""
    page_state = PageState()

    line1 = _line([_word("alpha", 0)], 0)
    line2 = _line([_word("beta", 20)], 20)
    para = _paragraph([line1, line2], 0)
    page = Page(width=100, height=100, page_index=0, items=[para])
    page.name = "page_001.png"

    page_state.current_page = page
    page_state.current_page_model = type(
        "PageModelStub",
        (),
        {"name": "page_001.png", "image_path": None},
    )()
    page_state._project = type(
        "ProjectStub",
        (),
        {
            "ground_truth_map": {"page_001.png": "alpha\nbeta"},
            "image_paths": [Path("/tmp/page_001.png")],
        },
    )()
    page_state._current_page_index = 0

    assert page_state.split_paragraph_after_line(0, 0) is True
    assert len(page.paragraphs) == 2
    assert all(len(paragraph.lines) == 1 for paragraph in page.paragraphs)


def test_split_paragraph_with_selected_lines_splits_selected_vs_unselected():
    """Split-by-selection should produce selected-lines and unselected-lines paragraphs."""
    page_state = PageState()

    line1 = _line([_word("alpha", 0)], 0)
    line2 = _line([_word("beta", 20)], 20)
    line3 = _line([_word("gamma", 40)], 40)
    para = _paragraph([line1, line2, line3], 0)
    page = Page(width=100, height=100, page_index=0, items=[para])
    page.name = "page_001.png"

    page_state.current_page = page
    page_state.current_page_model = type(
        "PageModelStub",
        (),
        {"name": "page_001.png", "image_path": None},
    )()
    page_state._project = type(
        "ProjectStub",
        (),
        {
            "ground_truth_map": {"page_001.png": "alpha\nbeta\ngamma"},
            "image_paths": [Path("/tmp/page_001.png")],
        },
    )()
    page_state._current_page_index = 0

    assert page_state.split_paragraph_with_selected_lines(0, [0, 2]) is True
    assert len(page.paragraphs) == 2
    assert [line.text for line in page.paragraphs[0].lines] == ["alpha", "gamma"]
    assert [line.text for line in page.paragraphs[1].lines] == ["beta"]


def test_split_line_after_word_splits_line_into_two_lines():
    """Splitting after a selected word should produce two lines in one paragraph."""
    page_state = PageState()

    line = _line([_word("alpha", 0), _word("beta", 20), _word("gamma", 40)], 0)
    para = _paragraph([line], 0)
    page = Page(width=120, height=100, page_index=0, items=[para])
    page.name = "page_001.png"

    page_state.current_page = page
    page_state.current_page_model = type(
        "PageModelStub",
        (),
        {"name": "page_001.png", "image_path": None},
    )()
    page_state._project = type(
        "ProjectStub",
        (),
        {
            "ground_truth_map": {"page_001.png": "alpha beta gamma"},
            "image_paths": [Path("/tmp/page_001.png")],
        },
    )()
    page_state._current_page_index = 0

    assert page_state.split_line_after_word(0, 0, 0) is True
    assert len(page.lines) == 2
    assert [word.text for word in page.lines[0].words] == ["alpha"]
    assert [word.text for word in page.lines[1].words] == ["beta", "gamma"]


def test_notify_continues_after_listener_exception():
    """A failing listener should not prevent later listeners from running."""
    page_state = PageState()
    seen: list[str] = []

    def failing_listener() -> None:
        seen.append("failing")
        raise RuntimeError("listener failure")

    def succeeding_listener() -> None:
        seen.append("succeeding")

    page_state.on_change = [failing_listener, succeeding_listener]

    page_state.notify()

    assert seen == ["failing", "succeeding"]


def test_split_line_with_selected_words_creates_one_new_line_from_selection():
    """Selected words should be extracted into one new line, not one-per-source-line."""
    page_state = PageState()

    line1 = _line([_word("alpha", 0), _word("beta", 20), _word("gamma", 40)], 0)
    line2 = _line([_word("delta", 0), _word("epsilon", 20), _word("zeta", 40)], 20)
    para = _paragraph([line1, line2], 0)
    page = Page(width=160, height=120, page_index=0, items=[para])
    page.name = "page_001.png"

    page_state.current_page = page
    page_state.current_page_model = type(
        "PageModelStub",
        (),
        {"name": "page_001.png", "image_path": None},
    )()
    page_state._project = type(
        "ProjectStub",
        (),
        {
            "ground_truth_map": {
                "page_001.png": "alpha beta gamma\ndelta epsilon zeta"
            },
            "image_paths": [Path("/tmp/page_001.png")],
        },
    )()
    page_state._current_page_index = 0

    assert (
        page_state.split_line_with_selected_words(0, [(0, 1), (1, 0), (1, 2)]) is True
    )
    assert len(page.lines) == 3
    line_signatures = [tuple(word.text for word in line.words) for line in page.lines]
    assert ("alpha", "gamma") in line_signatures
    assert ("epsilon",) in line_signatures
    assert tuple(sorted(("beta", "delta", "zeta"))) in [
        tuple(sorted(words)) for words in line_signatures
    ]


def test_group_selected_words_into_new_paragraph_moves_selected_words():
    """Grouping selected words should create a new paragraph with selected-word lines."""
    page_state = PageState()

    line1 = _line([_word("alpha", 0), _word("beta", 20), _word("gamma", 40)], 0)
    line2 = _line([_word("delta", 0), _word("epsilon", 20), _word("zeta", 40)], 20)
    para = _paragraph([line1, line2], 0)
    page = Page(width=160, height=100, page_index=0, items=[para])
    page.name = "page_001.png"

    page_state.current_page = page
    page_state.current_page_model = type(
        "PageModelStub",
        (),
        {"name": "page_001.png", "image_path": None},
    )()
    page_state._project = type(
        "ProjectStub",
        (),
        {
            "ground_truth_map": {
                "page_001.png": "alpha beta gamma\ndelta epsilon zeta"
            },
            "image_paths": [Path("/tmp/page_001.png")],
        },
    )()
    page_state._current_page_index = 0

    assert (
        page_state.group_selected_words_into_new_paragraph(0, [(0, 1), (1, 0)]) is True
    )
    assert len(page.paragraphs) == 2
    assert [word.text for word in page.paragraphs[0].lines[0].words] == [
        "alpha",
        "gamma",
    ]
    assert [word.text for word in page.paragraphs[0].lines[1].words] == [
        "epsilon",
        "zeta",
    ]
    new_paragraph_lines = [
        tuple(word.text for word in line.words) for line in page.paragraphs[1].lines
    ]
    assert sorted(new_paragraph_lines) == sorted(
        [
            ("beta",),
            ("delta",),
        ]
    )


def test_group_selected_words_into_new_paragraph_across_multiple_paragraphs():
    """Grouping should move selected words from multiple paragraphs into one new paragraph."""
    page_state = PageState()

    para1_line = _line([_word("alpha", 0), _word("beta", 20), _word("gamma", 40)], 0)
    para2_line = _line([_word("delta", 0), _word("epsilon", 20), _word("zeta", 40)], 20)
    para1 = _paragraph([para1_line], 0)
    para2 = _paragraph([para2_line], 20)
    page = Page(width=160, height=120, page_index=0, items=[para1, para2])
    page.name = "page_001.png"

    page_state.current_page = page
    page_state.current_page_model = type(
        "PageModelStub",
        (),
        {"name": "page_001.png", "image_path": None},
    )()
    page_state._project = type(
        "ProjectStub",
        (),
        {
            "ground_truth_map": {
                "page_001.png": "alpha beta gamma\ndelta epsilon zeta"
            },
            "image_paths": [Path("/tmp/page_001.png")],
        },
    )()
    page_state._current_page_index = 0

    selected_keys: list[tuple[int, int]] = []
    for line_index, line in enumerate(page.lines):
        for word_index, word in enumerate(line.words):
            if word.text in {"beta", "delta"}:
                selected_keys.append((line_index, word_index))

    assert page_state.group_selected_words_into_new_paragraph(0, selected_keys) is True
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


def test_persist_page_to_file_prefers_current_in_memory_page(tmp_path):
    """Saving current page should use in-memory edited page, not reload stale saved page."""
    page_state = PageState()

    image_path = tmp_path / "page_001.png"
    image_path.write_bytes(b"x")

    current_page = SimpleNamespace(
        image_path=str(image_path),
        index=0,
        name="page_001.png",
        page_source="ocr",
        ocr_provenance=None,
        to_dict=lambda: {"type": "page", "items": []},
    )

    page_state._project_root = tmp_path
    page_state._project = SimpleNamespace(source_lib="doctr-pgdp-labeled")
    page_state._current_page_index = 0
    page_state.current_page = current_page
    page_state.current_page_model = None

    get_page_model_calls = []

    def _unexpected_get_page_model(_page_index: int, force_ocr: bool = False):
        _ = force_ocr
        get_page_model_calls.append(_page_index)
        return None

    page_state.get_page_model = _unexpected_get_page_model  # type: ignore[method-assign]

    captured = {}

    def _save_page_stub(**kwargs):
        captured.update(kwargs)
        return True

    page_state.page_ops.save_page = _save_page_stub  # type: ignore[method-assign]

    assert page_state.persist_page_to_file(0) is True
    assert get_page_model_calls == []
    assert captured.get("page") is not None
    assert getattr(captured["page"], "page", None) is current_page


def test_auto_save_to_cache_does_not_mark_page_as_filesystem(tmp_path):
    """Auto-save cache writes should not switch source badge to LABELED."""
    page_state = PageState()

    image_path = tmp_path / "page_001.png"
    image_path.write_bytes(b"x")

    current_page = SimpleNamespace(
        image_path=str(image_path),
        index=0,
        name="page_001.png",
        page_source="ocr",
        ocr_provenance=None,
        to_dict=lambda: {"type": "page", "items": []},
    )

    page_state._project_root = tmp_path
    page_state._project = SimpleNamespace(source_lib="doctr-pgdp-labeled")
    page_state._current_page_index = 0
    page_state.current_page = current_page
    page_state.current_page_model = None

    set_source_calls: list[tuple[int, str]] = []

    class ProjectStateStub:
        def upsert_page_model(self, page_index, page, source):
            _ = (page_index, page, source)

        def get_page_model(self, _page_index):
            return None

        def set_page_source(self, page_index, source):
            set_source_calls.append((page_index, source))

    page_state._project_state = ProjectStateStub()

    page_state.page_ops.save_page = lambda **_kwargs: True  # type: ignore[method-assign]

    page_state._auto_save_to_cache()

    assert set_source_calls == []


def test_reload_page_with_ocr_invalidates_page_image_cache_and_refreshes_overlays(
    tmp_path, monkeypatch
):
    """Reload OCR should remove per-page image cache files and refresh overlays."""
    page_state = PageState()

    cache_root = tmp_path / "cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        PersistencePathsOperations,
        "get_page_image_cache_root",
        staticmethod(lambda: cache_root),
    )

    project_root = tmp_path / "book_project"
    project_root.mkdir(parents=True, exist_ok=True)
    page_state._project_root = project_root
    page_state._project = SimpleNamespace(pages=[SimpleNamespace()])

    matching_one = cache_root / f"{project_root.name}_001_paragraph_old.png"
    matching_two = cache_root / f"{project_root.name}_001_line_old.png"
    non_matching = cache_root / "different_project_001_word_old.png"
    matching_one.write_bytes(b"old")
    matching_two.write_bytes(b"old")
    non_matching.write_bytes(b"keep")

    class ReloadedPage:
        def __init__(self):
            self.refresh_calls = 0

        def refresh_page_images(self):
            self.refresh_calls += 1

    reloaded_page = ReloadedPage()
    reloaded_model = SimpleNamespace(
        index=0,
        page=reloaded_page,
        page_source="ocr",
        cached_image_filenames=["stale.png"],
    )

    class ProjectStateStub:
        def __init__(self):
            self.clear_calls = []

        def clear_page_model(self, page_index):
            self.clear_calls.append(page_index)

        def ensure_page_model(self, page_index, force_ocr=False):
            assert page_index == 0
            assert force_ocr is True
            return reloaded_model

    page_state._project_state = ProjectStateStub()

    page_state.reload_page_with_ocr(0)

    assert matching_one.exists() is False
    assert matching_two.exists() is False
    assert non_matching.exists() is True
    assert reloaded_page.refresh_calls == 1
    assert page_state.current_page_model is reloaded_model
    assert page_state.current_page_model.cached_image_filenames is None
    assert page_state._project_state.clear_calls == [0]
