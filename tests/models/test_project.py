from pathlib import Path
from unittest.mock import Mock

from pd_book_tools.ocr.page import Page

from ocr_labeler.models.project import Project


class TestProject:
    def test_initialization(self):
        """Test Project initialization with default values."""
        vm = Project()
        assert vm.pages == []
        assert vm.image_paths == []
        assert vm.ground_truth_map == {}

    def test_initialization_with_values(self):
        """Test Project initialization with provided values."""
        image_paths = [Path("test1.png"), Path("test2.png")]
        ground_truth_map = {"test1.png": "Ground truth 1"}
        vm = Project(image_paths=image_paths, ground_truth_map=ground_truth_map)
        assert vm.image_paths == image_paths
        assert vm.ground_truth_map == ground_truth_map

    def test_project_as_data_structure(self):
        """Test that Project now works as a pure data structure."""
        # Test that Project can hold data without loading behavior
        vm = Project(
            image_paths=[Path("test1.png"), Path("test2.png")],
            pages=[None, None],
            ground_truth_map={"test1.png": "Ground truth 1"},
        )

        # Verify data structure integrity
        assert len(vm.pages) == 2
        assert len(vm.image_paths) == 2
        assert vm.pages[0] is None  # Not loaded yet
        assert vm.pages[1] is None  # Not loaded yet
        assert vm.ground_truth_map["test1.png"] == "Ground truth 1"

        # Test that pages can be set directly (for state operations)
        mock_page = Mock(spec=Page)
        vm.pages[0] = mock_page
        assert vm.pages[0] == mock_page

    def test_page_count(self):
        """Test page_count method."""
        vm = Project()
        assert vm.page_count() == 0

        vm = Project(image_paths=[Path("1.png"), Path("2.png")], pages=[None, None])
        assert vm.page_count() == 2
