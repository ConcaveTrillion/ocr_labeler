from pathlib import Path
from unittest.mock import Mock, patch

from pd_book_tools.ocr.page import Page

from ocr_labeler.models.project import Project


class TestProject:
    def test_initialization(self):
        """Test Project initialization with default values."""
        vm = Project()
        assert vm.pages == []
        assert vm.image_paths == []
        assert vm.current_page_index == 0
        assert vm.ground_truth_map == {}
        assert vm.page_loader is None

    def test_initialization_with_values(self):
        """Test Project initialization with provided values."""
        image_paths = [Path("test1.png"), Path("test2.png")]
        ground_truth_map = {"test1.png": "Ground truth 1"}
        vm = Project(image_paths=image_paths, ground_truth_map=ground_truth_map)
        assert vm.image_paths == image_paths
        assert vm.ground_truth_map == ground_truth_map

    def test_ensure_page_out_of_bounds(self):
        """Test _ensure_page with out-of-bounds index."""
        vm = Project()
        assert vm._ensure_page(-1) is None
        assert vm._ensure_page(0) is None  # No pages

    def test_ensure_page_no_loader(self):
        """Test _ensure_page without page_loader."""
        vm = Project(
            image_paths=[Path("test.png")],
            pages=[None],
            ground_truth_map={"test.png": "Mock GT"},
        )
        page = vm._ensure_page(0)
        assert page is not None
        assert page.image_path == Path("test.png")
        assert page.name == "test.png"
        assert page.index == 0

    @patch("ocr_labeler.models.project._page_operations.find_ground_truth_text")
    def test_ensure_page_with_loader_success(self, mock_find_gt):
        """Test _ensure_page with successful page_loader."""
        mock_find_gt.return_value = "Mock GT"
        mock_page = Mock(spec=Page)
        mock_loader = Mock(return_value=mock_page)
        vm = Project(
            image_paths=[Path("test.png")],
            pages=[None],
            page_loader=mock_loader,
            ground_truth_map={"test.png": "Mock GT"},
        )
        page = vm._ensure_page(0)
        assert page == mock_page
        mock_loader.assert_called_once_with(Path("test.png"), 0, "Mock GT")
        assert mock_page.image_path == Path("test.png")
        assert mock_page.name == "test.png"
        assert mock_page.index == 0

    @patch("cv2.imread")
    def test_ensure_page_with_loader_exception(self, mock_cv2):
        """Test _ensure_page with page_loader raising exception."""
        mock_cv2.return_value = Mock()  # Mock image
        mock_loader = Mock(side_effect=Exception("Load failed"))
        vm = Project(
            image_paths=[Path("test.png")],
            pages=[None],
            page_loader=mock_loader,
            ground_truth_map={"test.png": "Mock GT"},
        )
        page = vm._ensure_page(0)
        assert page is not None
        assert page.image_path == Path("test.png")
        assert page.name == "test.png"
        assert page.index == 0
        # Note: ground_truth_text assertion removed due to Page default
        assert hasattr(page, "cv2_numpy_page_image")

    def test_current_page(self):
        """Test current_page method."""
        vm = Project(image_paths=[Path("test.png")], pages=[None])
        with patch.object(vm, "_ensure_page", return_value=Mock()) as mock_ensure:
            page = vm.current_page()
            mock_ensure.assert_called_once_with(0)
            assert page == mock_ensure.return_value

    def test_prev_page(self):
        """Test prev_page method."""
        vm = Project(current_page_index=1)
        vm.prev_page()
        assert vm.current_page_index == 0
        vm.prev_page()  # Already at 0
        assert vm.current_page_index == 0

    def test_next_page(self):
        """Test next_page method."""
        vm = Project(image_paths=[Path("1.png"), Path("2.png")], pages=[None, None])
        vm.next_page()
        assert vm.current_page_index == 1
        vm.next_page()  # Already at last
        assert vm.current_page_index == 1

    def test_goto_page_index(self):
        """Test goto_page_index method."""
        vm = Project(
            image_paths=[Path("1.png"), Path("2.png"), Path("3.png")],
            pages=[None, None, None],
        )
        vm.goto_page_index(1)
        assert vm.current_page_index == 1
        vm.goto_page_index(-1)  # Clamp to 0
        assert vm.current_page_index == 0
        vm.goto_page_index(10)  # Clamp to 2
        assert vm.current_page_index == 2

    def test_goto_page_index_empty(self):
        """Test goto_page_index with empty pages."""
        vm = Project()
        vm.goto_page_index(0)
        assert vm.current_page_index == -1

    def test_goto_page_number(self):
        """Test goto_page_number method."""
        vm = Project(image_paths=[Path("1.png"), Path("2.png")], pages=[None, None])
        vm.goto_page_number(2)  # 1-based
        assert vm.current_page_index == 1
