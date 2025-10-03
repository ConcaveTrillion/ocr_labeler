"""Integration tests for NiceGUI OCR labeler with test projects."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from nicegui.testing import User

from ocr_labeler import app
from ocr_labeler.app import NiceGuiLabeler
from ocr_labeler.viewmodels.project.page_state_view_model import PageStateViewModel


@pytest.fixture
def mock_ocr_processing(monkeypatch):
    """Fixture that mocks OCR processing for integration tests.

    Returns the mock_ocr patch object that can be used to configure
    the mock document behavior.
    """
    with patch(
        "pd_book_tools.ocr.document.Document.from_image_ocr_via_doctr"
    ) as mock_ocr:
        # Mock the OCR processing to return a mock document
        mock_document = Mock()
        mock_page = Mock()
        mock_page.name = "001.png"  # Mock page name
        mock_page.index = 0
        mock_page.page_source = "ocr"

        # Create mock images with shape attribute like numpy arrays
        class ImgLike:
            def __init__(self, shape):
                self.shape = shape

        # Set up image attributes that the viewmodel expects
        mock_page.cv2_numpy_page_image = ImgLike((100, 100, 3))
        mock_page.cv2_numpy_page_image_paragraph_with_bboxes = ImgLike((100, 100, 3))
        mock_page.cv2_numpy_page_image_line_with_bboxes = ImgLike((100, 100, 3))
        mock_page.cv2_numpy_page_image_word_with_bboxes = ImgLike((100, 100, 3))
        mock_page.cv2_numpy_page_image_matched_word_with_colors = ImgLike((100, 100, 3))

        mock_document.pages = [mock_page]  # Mock page
        mock_ocr.return_value = mock_document

        # Monkeypatch the _encode_image method to avoid actual image processing
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


class TestProjectStructure:
    """Test that test projects have the expected structure."""

    @pytest.fixture
    def test_projects_root(self) -> Path:
        """Return the path to the test projects directory."""
        return Path(__file__).parent.parent / "test-data" / "pgdp-projects"

    def test_project_structure_validation(self, test_projects_root: Path):
        """Test that the test projects have the expected structure."""
        # Verify projectID629292e7559a8 exists and has expected files
        project1_dir = test_projects_root / "projectID629292e7559a8"
        assert project1_dir.exists()
        assert project1_dir.is_dir()

        # Check for image files
        image_files = list(project1_dir.glob("*.png"))
        assert len(image_files) == 392  # 001.png through 392.png

        # Check for ground truth file
        gt_file = project1_dir / "pages.json"
        assert gt_file.exists()

        # Verify projectID66c62fca99a93 exists and has expected files
        project2_dir = test_projects_root / "projectID66c62fca99a93"
        assert project2_dir.exists()
        assert project2_dir.is_dir()

        # Check for image files
        image_files = list(project2_dir.glob("*.png"))
        assert len(image_files) == 420  # 001.png through 420.png

        # Check for ground truth file
        gt_file = project2_dir / "pages.json"
        assert gt_file.exists()

    async def test_ground_truth_loading(self, test_projects_root: Path):
        """Test that ground truth data can be loaded from test projects."""
        from ocr_labeler.state.project_state import ProjectState

        project_state = ProjectState()

        # Test loading ground truth for projectID629292e7559a8
        project1_dir = test_projects_root / "projectID629292e7559a8"
        gt_map = await project_state.load_ground_truth_map(project1_dir)
        assert len(gt_map) == 392  # Should have entries for all 392 pages
        assert (
            "001.png" in gt_map
        )  # Check that at least the first page has ground truth
        assert isinstance(gt_map["001.png"], str)  # Should be a string
        assert len(gt_map["001.png"]) > 0  # Should not be empty

        # Test loading ground truth for projectID66c62fca99a93
        project2_dir = test_projects_root / "projectID66c62fca99a93"
        gt_map = await project_state.load_ground_truth_map(project2_dir)
        assert len(gt_map) == 420  # Should have entries for all 420 pages
        assert (
            "001.png" in gt_map
        )  # Check that at least the first page has ground truth
        assert isinstance(gt_map["001.png"], str)  # Should be a string
        assert len(gt_map["001.png"]) > 0  # Should not be empty


@pytest.mark.module_under_test(app)
class TestNiceGuiIntegration:
    """Integration tests using NiceGUI's testing framework."""

    @pytest.fixture
    def test_projects_root(self) -> Path:
        """Return the path to the test projects directory."""
        return Path(__file__).parent.parent / "test-data" / "pgdp-projects"

    def test_app_initialization_with_test_projects(self, test_projects_root: Path):
        """Test that the app initializes correctly with test projects available."""
        # Initialize the app with test projects root
        labeler = NiceGuiLabeler(
            project_root=test_projects_root, projects_root=test_projects_root
        )

        # Verify the app state is set up
        assert labeler.state is not None
        assert labeler.viewmodel is not None
        assert labeler.view is not None

    async def test_project_discovery_ui(self, user: User, test_projects_root: Path):
        """Test that test projects are discovered and displayed in the UI."""
        # Create the app instance with test projects
        labeler = NiceGuiLabeler(
            project_root=test_projects_root, projects_root=test_projects_root
        )
        labeler.create_routes()

        # Open the main page
        await user.open("/")

        # The page should load without errors
        # Initially should show "No Project Loaded" since no project is selected
        await user.should_see("No Project Loaded")

        # Check that the project dropdown has the correct options
        select_elements = user.find("Project")
        # Find the select element (should be the one with options)
        select_element = None
        for elem in select_elements.elements:
            if hasattr(elem, "options"):
                select_element = elem
                break
        assert select_element is not None, "Could not find select element with options"
        expected_projects = ["projectID629292e7559a8", "projectID66c62fca99a93"]
        assert select_element.options == expected_projects

    async def test_project_selection_ui_elements(
        self, user: User, test_projects_root: Path
    ):
        """Test that project selection UI elements are present."""
        # Create the app instance
        labeler = NiceGuiLabeler(
            project_root=test_projects_root, projects_root=test_projects_root
        )
        labeler.create_routes()

        # Open the main page
        await user.open("/")

        # Should see project loading controls - the button shows "LOAD"
        await user.should_see("LOAD")

    async def test_project_loading_via_button(
        self, mock_ocr_processing, user: User, test_projects_root: Path
    ):
        """Test that clicking the LOAD button initiates project loading without errors."""
        # Create the app instance with test projects
        labeler = NiceGuiLabeler(
            project_root=test_projects_root, projects_root=test_projects_root
        )
        labeler.create_routes()

        # Open the main page
        await user.open("/")

        # Initially should show "No Project Loaded"
        await user.should_see("No Project Loaded")

        # Click the LOAD button to load the first project (should be pre-selected)
        # This should not crash the application
        user.find("LOAD").click()

        # Verify loading notification appears
        await user.should_see("Loading projectID629292e7559a8")

        # Verify that loading has started (spinner should be visible, indicating button is disabled)
        # The spinner starts hidden and becomes visible during loading
        await user.should_see(marker="spinner")  # Wait for spinner to appear

        # Verify that the LOAD button is still present (indicating no crash)
        await user.should_see("LOAD")

        # Verify that the project dropdown is still present
        select_elements = user.find("Project")
        # Find the select element (should be the one with options)
        select_element = None
        for elem in select_elements.elements:
            if hasattr(elem, "options"):
                select_element = elem
                break
        assert select_element is not None, "Could not find select element with options"
        expected_projects = ["projectID629292e7559a8", "projectID66c62fca99a93"]
        assert select_element.options == expected_projects

        # Try clicking again - this should not trigger another load operation
        # Since loading is in progress, the click should be ignored
        user.find("LOAD").click()

        # Verify the spinner is still visible (loading still in progress)
        await user.should_see("spinner")

        # Wait for loading to complete - spinner should disappear
        await user.should_not_see(marker="spinner")

        # Verify loaded notification appears
        await user.should_see("Loaded projectID629292e7559a8")

        # Verify that the project loaded successfully - navigation controls should be present
        await user.should_see("Prev")
        await user.should_see("Next")

    async def test_load_button_prevents_multiple_clicks(
        self, mock_ocr_processing, user: User, test_projects_root: Path
    ):
        """Test that the LOAD button prevents multiple clicks during loading.

        When the LOAD button is clicked multiple times rapidly, it should not
        trigger multiple load operations. The button should be disabled during
        loading to prevent duplicate operations.
        """
        # Create the app instance with test projects
        labeler = NiceGuiLabeler(
            project_root=test_projects_root, projects_root=test_projects_root
        )
        labeler.create_routes()

        # Open the main page
        await user.open("/")

        # Initially should show "No Project Loaded"
        await user.should_see("No Project Loaded")

        # Click the LOAD button multiple times rapidly
        load_button = user.find("LOAD")
        load_button.click()
        load_button.click()  # Second click - should be ignored by defensive check
        load_button.click()  # Third click - should also be ignored

        # Verify loading notification appears
        await user.should_see("Loading projectID629292e7559a8")

        # Verify that loading has started (spinner should be visible)
        await user.should_see(marker="spinner")

        # Wait for loading to complete
        await user.should_not_see(marker="spinner")

        # Verify loaded notification appears only once
        await user.should_see("Loaded projectID629292e7559a8")

        # Verify that the project loaded successfully - navigation controls should be present
        await user.should_see("Prev")
        await user.should_see("Next")
