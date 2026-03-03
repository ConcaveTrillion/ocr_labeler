from pathlib import Path

from pd_book_tools.geometry.bounding_box import BoundingBox
from pd_book_tools.geometry.point import Point
from pd_book_tools.ocr.block import Block, BlockCategory, BlockChildType
from pd_book_tools.ocr.page import Page
from pd_book_tools.ocr.word import Word

from ocr_labeler.state.page_state import PageState


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
