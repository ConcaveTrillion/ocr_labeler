"""Integration tests for URL routing (project and page routes)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from nicegui.elements.number import Number
from nicegui.testing import User

from ocr_labeler.app import NiceGuiLabeler
from ocr_labeler.viewmodels.project.page_state_view_model import PageStateViewModel


@pytest.fixture
def mock_ocr_processing(monkeypatch):
    """Fixture that mocks OCR processing for integration tests."""
    mock_predictor = Mock()
    mock_imread = Mock(return_value=Mock(shape=(100, 100, 3)))

    with (
        patch(
            "pd_book_tools.ocr.doctr_support.get_default_doctr_predictor",
            return_value=mock_predictor,
        ),
        patch(
            "pd_book_tools.ocr.document.Document.from_image_ocr_via_doctr"
        ) as mock_ocr,
        patch(
            "cv2.imread",
            mock_imread,
        ),
    ):
        mock_document = Mock()
        mock_page = Mock()
        mock_page.name = "001.png"
        mock_page.index = 0
        mock_page.page_source = "ocr"

        class ImgLike:
            def __init__(self, shape):
                self.shape = shape

        mock_page.cv2_numpy_page_image = ImgLike((100, 100, 3))
        mock_page.cv2_numpy_page_image_paragraph_with_bboxes = ImgLike((100, 100, 3))
        mock_page.cv2_numpy_page_image_line_with_bboxes = ImgLike((100, 100, 3))
        mock_page.cv2_numpy_page_image_word_with_bboxes = ImgLike((100, 100, 3))
        mock_page.cv2_numpy_page_image_matched_word_with_colors = ImgLike((100, 100, 3))

        mock_word = Mock()
        mock_word.crop_bottom = Mock()
        mock_word.expand_to_content = Mock()
        mock_block = Mock()
        mock_block.words = [mock_word]
        mock_page.blocks = [mock_block]
        mock_page.refine_bounding_boxes = Mock()
        mock_page.refresh_page_images = Mock()

        mock_document.pages = [mock_page]
        mock_ocr.return_value = mock_document

        def fake_encode_image(self, img):
            if hasattr(img, "shape"):
                return f"data:image/png;base64,fake_encoded_image_{img.shape}"
            return ""

        monkeypatch.setattr(
            PageStateViewModel,
            "_encode_image",
            fake_encode_image,
        )

        yield mock_ocr


@pytest.mark.nicegui_main_file(None)
class TestProjectRouting:
    """Integration tests for /project/{project_id} route."""

    @pytest.fixture
    def test_projects_root(self) -> Path:
        return Path(__file__).parent.parent / "test-data" / "pgdp-projects"

    @pytest.mark.nicegui_main_file(None)
    async def test_project_route_loads_project(
        self, mock_ocr_processing, user: User, test_projects_root: Path
    ):
        """Test that /project/{project_id} loads the correct project."""
        labeler = NiceGuiLabeler(
            project_root=test_projects_root,
            projects_root=test_projects_root,
            enable_session_logging=False,
        )
        labeler.create_routes()

        project_id = "projectID629292e7559a8"
        await user.open(f"/project/{project_id}")

        # Route should resolve to first page (canonical page/1 behavior)
        await user.should_see("Prev")
        await user.should_see("Next")
        number_inputs = user.find(kind=Number).elements
        assert number_inputs, "Expected to find page number input"
        page_number_input = next(iter(number_inputs))
        assert page_number_input.value == 1

    @pytest.mark.nicegui_main_file(None)
    async def test_project_route_nonexistent_shows_warning(
        self, user: User, test_projects_root: Path
    ):
        """Test that /project/{nonexistent} shows a warning notification."""
        labeler = NiceGuiLabeler(
            project_root=test_projects_root,
            projects_root=test_projects_root,
            enable_session_logging=False,
        )
        labeler.create_routes()

        await user.open("/project/nonexistent_project_xyz")

        # Should still render the base UI (project selector, etc.)
        await user.should_see("No Project Loaded")

    @pytest.mark.nicegui_main_file(None)
    async def test_project_page_route_loads_project(
        self, mock_ocr_processing, user: User, test_projects_root: Path
    ):
        """Test that /project/{id}/page/{page} loads the correct project."""
        labeler = NiceGuiLabeler(
            project_root=test_projects_root,
            projects_root=test_projects_root,
            enable_session_logging=False,
        )
        labeler.create_routes()

        project_id = "projectID629292e7559a8"
        await user.open(f"/project/{project_id}/page/2")

        # Should show navigation controls after project loads
        await user.should_see("Prev")
        await user.should_see("Next")
        number_inputs = user.find(kind=Number).elements
        assert number_inputs, "Expected to find page number input"
        page_number_input = next(iter(number_inputs))
        assert page_number_input.value == 2

    @pytest.mark.nicegui_main_file(None)
    async def test_root_route_reconnect_path_restores_project_page(
        self,
        mock_ocr_processing,
        user: User,
        test_projects_root: Path,
        monkeypatch,
    ):
        """Root route should restore project/page when reconnect path is recovered."""
        labeler = NiceGuiLabeler(
            project_root=test_projects_root,
            projects_root=test_projects_root,
            enable_session_logging=False,
        )

        project_id = "projectID629292e7559a8"
        monkeypatch.setattr(
            labeler,
            "_get_request_path",
            lambda: f"/project/{project_id}/page/2",
        )

        labeler.create_routes()

        await user.open("/")

        await user.should_see("Prev")
        await user.should_see("Next")
        number_inputs = user.find(kind=Number).elements
        assert number_inputs, "Expected to find page number input"
        page_number_input = next(iter(number_inputs))
        assert page_number_input.value == 2


@pytest.mark.nicegui_main_file(None)
class TestSessionCreation:
    """Tests for the _create_session helper used by all route handlers."""

    @pytest.fixture
    def test_projects_root(self) -> Path:
        return Path(__file__).parent.parent / "test-data" / "pgdp-projects"

    def test_create_session_stores_no_per_session_state_on_app(
        self, test_projects_root: Path
    ):
        """Verify _create_session doesn't store state/viewmodel/view on self."""
        app = NiceGuiLabeler(
            project_root=test_projects_root,
            projects_root=test_projects_root,
            enable_session_logging=False,
        )

        # The app should not have state, viewmodel, or view attrs
        assert not hasattr(app, "state") or app.__dict__.get("state") is None
        assert not hasattr(app, "viewmodel") or app.__dict__.get("viewmodel") is None
        assert not hasattr(app, "view") or app.__dict__.get("view") is None

    @pytest.mark.nicegui_main_file(None)
    async def test_root_route_renders_ui(self, user: User, test_projects_root: Path):
        """Test that the root route renders the basic UI."""
        labeler = NiceGuiLabeler(
            project_root=test_projects_root,
            projects_root=test_projects_root,
            enable_session_logging=False,
        )
        labeler.create_routes()

        await user.open("/")
        await user.should_see("No Project Loaded")
        await user.should_see("LOAD")
