import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from ocr_labeler.state.page_state import PageState
from ocr_labeler.state.project_state import ProjectState
from ocr_labeler.viewmodels.project import page_state_view_model as vm_module
from ocr_labeler.viewmodels.project.page_state_view_model import PageStateViewModel

logger = logging.getLogger(__name__)


class DummyPage:
    def __init__(self, name="dummy.png"):
        self.name = name


class DummyProject:
    def __init__(self, image_paths):
        self.image_paths = image_paths


def test_pagesate_viewmodel_binds_to_page_state_directly(tmp_path, monkeypatch):
    # Setup a minimal project and page state
    project_state = ProjectState()
    project_state.project = type("P", (), {"pages": [None], "ground_truth_map": {}})()
    page_state = PageState()

    # Set project context so page_state has project reference
    page_state.set_project_context(project_state.project, tmp_path, project_state)

    # Create a dummy page and set it on the project's pages list
    dummy_page = DummyPage()
    project_state.project.pages[0] = dummy_page

    # Bind viewmodel directly to PageState
    vm = PageStateViewModel(page_state)

    # Ensure we can call update image sources without raising
    vm._update_image_sources()

    # Ensure image sources properties exist (even if empty)
    assert hasattr(vm, "original_image_source")
    assert hasattr(vm, "paragraphs_image_source")


def test_pagesate_viewmodel_rebinds_on_project_state_navigation(tmp_path, monkeypatch):
    # Setup ProjectState with two pages
    ps = ProjectState()
    # Create a fake project with image_paths and placeholder None pages
    fake_project = type("P", (), {})()
    fake_project.image_paths = [Path("a.png"), Path("b.png")]
    fake_project.pages = [None, None]
    fake_project.ground_truth_map = {}
    ps.project = fake_project
    ps.project_root = tmp_path

    # Ensure get_page_state will create PageState instances
    ps.get_page_state(0)
    ps.get_page_state(1)

    # Put a dummy page object into the first and second page via ProjectState.ensure_page
    fake_first_page = DummyPage("a.png")
    fake_second_page = DummyPage("b.png")
    # Simulate project pages being loaded
    ps.project.pages[0] = fake_first_page
    ps.project.pages[1] = fake_second_page

    # Create the viewmodel with the ProjectState (the code should bind to current page state)
    ps.current_page_index = 0
    vm = PageStateViewModel(ps)

    # Initially bound to first page's PageState
    # Trigger update -> should not raise and should reflect first page
    vm._update_image_sources()

    # Now navigate project state to page 1 and notify listeners
    ps.current_page_index = 1
    ps.notify()

    # After notify, the viewmodel should be rebound to the second page state and be usable
    vm._update_image_sources()

    # Sanity: ensure vm._page_state is one of the page states returned by ps.get_page_state
    assert vm._page_state in (ps.get_page_state(0), ps.get_page_state(1))


def test_image_sources_change_after_rebind_with_mocked_encoder(tmp_path, monkeypatch):
    """Verify that image-related properties update when the viewmodel rebinds to a new page.

    We mock the page's image attributes and the viewmodel's encoder to return distinct
    string values so we can assert the rebind changes the image sources.
    """
    ps = ProjectState()
    fake_project = type("P", (), {})()
    fake_project.image_paths = [Path("a.png"), Path("b.png")]
    fake_project.pages = [None, None]
    fake_project.ground_truth_map = {}
    ps.project = fake_project
    ps.project_root = tmp_path

    # Ensure page states exist
    ps.get_page_state(0)
    ps.get_page_state(1)

    # Create two dummy page objects with simple numpy-like placeholders
    class ImgLike:
        def __init__(self, shape):
            self.shape = shape

    fake_first_page = DummyPage("a.png")
    fake_second_page = DummyPage("b.png")
    fake_first_page.index = 0
    fake_first_page.page_source = "ocr"
    fake_first_page.cv2_numpy_page_image = ImgLike((10, 10, 3))

    fake_second_page.index = 1
    fake_second_page.page_source = "filesystem"
    fake_second_page.cv2_numpy_page_image = ImgLike((20, 20, 3))

    # Attach the fake pages into the project's pages so ensure_page will return them
    ps.project.pages[0] = fake_first_page
    ps.project.pages[1] = fake_second_page

    # Create viewmodel bound to the ProjectState
    ps.current_page_index = 0
    vm = PageStateViewModel(ps)

    # Monkeypatch the _encode_image method to return distinct markers per image object
    def fake_encode(self, img):
        if getattr(img, "shape", None) == (10, 10, 3):
            return "ENCODED-FIRST"
        if getattr(img, "shape", None) == (20, 20, 3):
            return "ENCODED-SECOND"
        return ""

    monkeypatch.setattr(
        PageStateViewModel,
        "_encode_image",
        fake_encode,
    )

    # Initial update should set image source from first page
    vm._update_image_sources()
    first_src = vm.original_image_source
    first_index = vm.page_index
    first_page_source = vm.page_source

    assert first_src == "ENCODED-FIRST"
    assert first_index == 0
    assert first_page_source == "ocr"

    # Now navigate to second page and notify project listeners to trigger rebind
    ps.current_page_index = 1
    ps.notify()

    # After notify, the viewmodel should rebind and update image sources
    vm._update_image_sources()
    second_src = vm.original_image_source
    second_index = vm.page_index
    second_page_source = vm.page_source

    assert second_src == "ENCODED-SECOND"
    assert second_index == 1
    assert second_page_source == "filesystem"


def test_apply_encoded_results_skips_duplicate_callback_payload(tmp_path):
    project_state = ProjectState()
    project_state.project = type("P", (), {"pages": [None], "ground_truth_map": {}})()
    page_state = PageState()
    page_state.set_project_context(project_state.project, tmp_path, project_state)

    vm = PageStateViewModel(page_state)
    callback = MagicMock()
    vm.set_image_update_callback(callback)

    payload = [("original_image_source", "data:image/png;base64,AAA")]

    vm._apply_encoded_results(payload, current_page=SimpleNamespace(name="p1"))
    vm._apply_encoded_results(payload, current_page=SimpleNamespace(name="p1"))

    callback.assert_called_once_with(
        {"original_image_source": "data:image/png;base64,AAA"}
    )


def test_schedule_image_update_skips_when_already_scheduled(tmp_path, monkeypatch):
    project_state = ProjectState()
    project_state.project = type("P", (), {"pages": [None], "ground_truth_map": {}})()
    page_state = PageState()
    page_state.set_project_context(project_state.project, tmp_path, project_state)

    vm = PageStateViewModel(page_state)

    create_calls: list[object] = []

    def fake_create(coro):
        create_calls.append(coro)

    monkeypatch.setattr(vm_module.background_tasks, "create", fake_create)

    vm._schedule_image_update()
    vm._schedule_image_update()

    assert len(create_calls) == 1
    create_calls[0].close()
