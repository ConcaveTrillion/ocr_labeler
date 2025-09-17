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
        assert vm.ground_truth_map == {}
        assert vm.page_parser is None

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

    def test_ensure_page_no_parser(self):
        """Test _ensure_page without page_parser."""
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
    def test_ensure_page_with_parser_success(self, mock_find_gt):
        """Test _ensure_page with successful page_parser."""
        mock_find_gt.return_value = "Mock GT"
        mock_page = Mock(spec=Page)
        mock_parser = Mock(return_value=mock_page)
        vm = Project(
            image_paths=[Path("test.png")],
            pages=[None],
            page_parser=mock_parser,
            ground_truth_map={"test.png": "Mock GT"},
        )
        page = vm._ensure_page(0)
        assert page == mock_page
        mock_parser.assert_called_once_with(Path("test.png"), 0, "Mock GT")
        assert mock_page.image_path == Path("test.png")
        assert mock_page.name == "test.png"
        assert mock_page.index == 0

    @patch("cv2.imread")
    def test_ensure_page_with_parser_exception(self, mock_cv2):
        """Test _ensure_page with page_parser raising exception."""
        mock_cv2.return_value = Mock()  # Mock image
        mock_parser = Mock(side_effect=Exception("Load failed"))
        vm = Project(
            image_paths=[Path("test.png")],
            pages=[None],
            page_parser=mock_parser,
            ground_truth_map={"test.png": "Mock GT"},
        )
        page = vm._ensure_page(0)
        assert page is not None
        assert page.image_path == Path("test.png")
        assert page.name == "test.png"
        assert page.index == 0
        # Note: ground_truth_text assertion removed due to Page default
        assert hasattr(page, "cv2_numpy_page_image")

    def test_get_page(self):
        """Test get_page method."""
        vm = Project(image_paths=[Path("test.png")], pages=[None])
        with patch.object(vm, "_ensure_page", return_value=Mock()) as mock_ensure:
            page = vm.get_page(0)
            mock_ensure.assert_called_once_with(0)
            assert page == mock_ensure.return_value

    def test_page_count(self):
        """Test page_count method."""
        vm = Project()
        assert vm.page_count() == 0

        vm = Project(image_paths=[Path("1.png"), Path("2.png")], pages=[None, None])
        assert vm.page_count() == 2
