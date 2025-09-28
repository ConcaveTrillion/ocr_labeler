"""Integration tests for NiceGUI OCR labeler with test projects."""

from __future__ import annotations

from pathlib import Path

import pytest
from nicegui.testing import User

from ocr_labeler import app
from ocr_labeler.app import NiceGuiLabeler


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
