"""Tests for page operations."""

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pd_book_tools.ocr.page import Page

from ocr_labeler.operations.ocr.page_operations import PageLoadInfo, PageOperations


class TestPageLoadInfo:
    """Test PageLoadInfo named tuple."""

    def test_page_load_info_creation(self):
        """Test creating PageLoadInfo with valid data."""
        info = PageLoadInfo(
            can_load=True,
            json_filename="test_001.json",
            json_path=Path("/tmp/test_001.json"),
            file_prefix="test_001",
        )
        assert info.can_load is True
        assert info.json_filename == "test_001.json"
        assert info.json_path == Path("/tmp/test_001.json")
        assert info.file_prefix == "test_001"


class TestPageOperations:
    """Test PageOperations class methods."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def operations(self):
        """Create PageOperations instance for testing."""
        return PageOperations()

    def test_build_initial_page_parser(self, operations):
        """Test building the initial page parser."""
        parser = operations.build_initial_page_parser()
        assert callable(parser)

    @patch("pd_book_tools.ocr.doctr_support.get_default_doctr_predictor")
    @patch("pd_book_tools.ocr.document.Document.from_image_ocr_via_doctr")
    @patch("cv2.imread")
    def test_page_parser_execution(
        self, mock_cv2_imread, mock_from_image_ocr, mock_get_predictor, temp_dir
    ):
        """Test the page parser execution with mocked dependencies."""
        # Setup mocks
        mock_predictor = MagicMock()
        mock_get_predictor.return_value = mock_predictor

        mock_page = MagicMock(spec=Page)
        mock_page.name = "test_page"
        mock_page.text = "OCR text"
        mock_doc = MagicMock()
        mock_doc.pages = [mock_page]
        mock_from_image_ocr.return_value = mock_doc

        mock_cv2_imread.return_value = MagicMock()  # Mock image array

        operations = PageOperations()
        parser = operations.page_parser

        # Execute parser
        image_path = temp_dir / "test.png"
        image_path.touch()  # Create empty file
        result_page = parser(image_path, 0, "ground truth text")

        # Verify results
        assert result_page == mock_page
        mock_from_image_ocr.assert_called_once()
        mock_cv2_imread.assert_called_once_with(str(image_path))

    def test_save_page_success(self, operations, temp_dir):
        """Test successful page saving."""
        # Create a mock page with required attributes
        page = MagicMock(spec=Page)
        page.index = 0  # 0-based index
        page.image_path = temp_dir / "source.png"
        page.to_dict.return_value = {
            "type": "page",
            "width": 100,
            "height": 100,
            "page_index": 0,
            "bounding_box": None,
            "items": [],
        }
        (temp_dir / "source.png").touch()  # Create source image file

        project_root = temp_dir / "project"
        project_root.mkdir()

        # Save the page
        success = operations.save_page(
            page=page,
            project_root=project_root,
            save_directory=str(temp_dir / "output"),
            project_id="test_project",
        )

        assert success is True

        # Verify files were created
        output_dir = temp_dir / "output"
        assert (output_dir / "test_project_001.png").exists()
        assert (output_dir / "test_project_001.json").exists()

        # Verify JSON content
        with open(output_dir / "test_project_001.json", "r") as f:
            json_data = json.load(f)

        assert json_data["schema"]["name"] == "ocr_labeler.user_page"
        assert json_data["schema"]["version"] == "2.0"
        assert json_data["source"]["image_path"] == "source.png"
        assert json_data["payload"]["page"]["type"] == "page"

    def test_save_page_includes_ocr_models_when_available(self, operations, temp_dir):
        """Test save_page persists OCR model metadata when predictor details exist."""

        class DummyComponent:
            def __init__(self, arch: str, weights_path: str):
                self.arch = arch
                self.weights_path = weights_path

        operations._docTR_predictor = SimpleNamespace(
            det_predictor=DummyComponent("db_resnet50", "detector.ckpt"),
            reco_predictor=DummyComponent("crnn_vgg16_bn", "recognizer.ckpt"),
        )

        page = MagicMock(spec=Page)
        page.index = 0
        page.image_path = temp_dir / "source.png"
        page.to_dict.return_value = {
            "type": "page",
            "width": 100,
            "height": 100,
            "page_index": 0,
            "items": [],
        }
        page._ocr_labeler_live_ocr_provenance = operations._build_live_ocr_provenance(
            source_lib="doctr-pgdp-labeled"
        )
        (temp_dir / "source.png").touch()

        project_root = temp_dir / "project"
        project_root.mkdir()

        success = operations.save_page(
            page=page,
            project_root=project_root,
            save_directory=str(temp_dir / "output"),
            project_id="test_project",
        )

        assert success is True

        output_dir = temp_dir / "output"
        with open(output_dir / "test_project_001.json", "r", encoding="utf-8") as f:
            json_data = json.load(f)

        models = json_data["provenance"]["ocr"]["models"]
        model_names = {model["name"] for model in models}
        assert "db_resnet50" in model_names
        assert "crnn_vgg16_bn" in model_names
        assert "engine_version" in json_data["provenance"]["ocr"]

    def test_save_page_no_image_path(self, operations, temp_dir):
        """Test saving page without image path."""
        page = MagicMock(spec=Page)
        page.index = 0

        project_root = temp_dir / "project"
        project_root.mkdir()

        success = operations.save_page(
            page=page,
            project_root=project_root,
            save_directory=str(temp_dir / "output"),
        )

        assert success is False

    def test_save_page_invalid_image_extension(self, operations, temp_dir):
        """Test saving page with invalid image extension."""
        page = MagicMock(spec=Page)
        page.index = 0
        page.image_path = temp_dir / "source.bmp"  # Invalid extension
        page.to_dict.return_value = {
            "type": "page",
            "width": 100,
            "height": 100,
            "page_index": 0,
            "bounding_box": None,
            "items": [],
        }
        (temp_dir / "source.bmp").touch()

        project_root = temp_dir / "project"
        project_root.mkdir()

        success = operations.save_page(
            page=page,
            project_root=project_root,
            save_directory=str(temp_dir / "output"),
            project_id="test_project",
        )

        assert success is True

        # Should default to .png extension
        output_dir = temp_dir / "output"
        assert (output_dir / "test_project_001.png").exists()

    def test_load_page_success(self, operations, temp_dir):
        """Test successful page loading."""
        # First save a page
        page = MagicMock(spec=Page)
        page.index = 0
        page.image_path = temp_dir / "source.png"
        page.to_dict.return_value = {
            "type": "page",
            "width": 100,
            "height": 100,
            "page_index": 0,
            "bounding_box": None,
            "items": [],
        }
        (temp_dir / "source.png").touch()

        project_root = temp_dir / "project"
        project_root.mkdir()

        operations.save_page(
            page=page,
            project_root=project_root,
            save_directory=str(temp_dir / "output"),
            project_id="test_project",
        )

        # Now load it back
        loaded_result = operations.load_page_model(
            page_number=1,  # 1-based
            project_root=project_root,
            save_directory=str(temp_dir / "output"),
            project_id="test_project",
        )

        assert loaded_result is not None
        loaded_page_model, _ = loaded_result
        loaded_page = loaded_page_model.page
        assert loaded_page.page_index == 0  # Should be restored from dict

    def test_load_page_not_found(self, operations, temp_dir):
        """Test loading non-existent page."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        loaded_result = operations.load_page_model(
            page_number=1,
            project_root=project_root,
            save_directory=str(temp_dir / "output"),
        )

        assert loaded_result is None

    def test_load_page_invalid_json(self, operations, temp_dir):
        """Test loading page with invalid JSON."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        # Create invalid JSON file
        json_file = output_dir / "project_001.json"
        with open(json_file, "w") as f:
            f.write("invalid json content")

        loaded_result = operations.load_page_model(
            page_number=1,
            project_root=project_root,
            save_directory=str(temp_dir / "output"),
        )

        assert loaded_result is None

    def test_load_page_legacy_json_format(self, operations, temp_dir):
        """Test that legacy flat JSON format remains loadable."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        legacy_json = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "source.png",
            "pages": [
                {
                    "type": "page",
                    "width": 100,
                    "height": 100,
                    "page_index": 0,
                    "items": [],
                }
            ],
        }
        with open(output_dir / "test_project_001.json", "w", encoding="utf-8") as f:
            json.dump(legacy_json, f)

        (output_dir / "test_project_001.png").touch()

        loaded_result = operations.load_page_model(
            page_number=1,
            project_root=project_root,
            save_directory=str(output_dir),
            project_id="test_project",
        )

        assert loaded_result is not None
        loaded_page_model, _ = loaded_result
        loaded_page = loaded_page_model.page
        assert loaded_page.page_index == 0

    def test_save_page_preserves_loaded_empty_models_without_rerun(
        self,
        operations,
        temp_dir,
    ):
        """Loaded `models: []` should not be backfilled from current predictor unless OCR reruns."""

        class DummyComponent:
            def __init__(self, arch: str, weights_path: str):
                self.arch = arch
                self.weights_path = weights_path

        operations._docTR_predictor = SimpleNamespace(
            det_predictor=DummyComponent("db_resnet50", "detector.ckpt"),
            reco_predictor=DummyComponent("crnn_vgg16_bn", "recognizer.ckpt"),
        )

        project_root = temp_dir / "project"
        project_root.mkdir()

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        v2_json = {
            "schema": {"name": "ocr_labeler.user_page", "version": "2.0"},
            "provenance": {
                "saved_at": "2026-02-15T00:00:00Z",
                "saved_by": "Save Page",
                "source_lane": "labeled",
                "app": {"name": "ocr_labeler", "version": "0.1.0"},
                "toolchain": {"python": "3.13.3", "pd_book_tools": "0.2.0"},
                "ocr": {
                    "engine": "doctr",
                    "models": [],
                },
            },
            "source": {
                "project_id": "test_project",
                "page_index": 0,
                "page_number": 1,
                "image_path": "source.png",
            },
            "payload": {
                "page": {
                    "type": "page",
                    "width": 100,
                    "height": 100,
                    "page_index": 0,
                    "items": [],
                }
            },
        }
        with open(output_dir / "test_project_001.json", "w", encoding="utf-8") as f:
            json.dump(v2_json, f)

        (project_root / "source.png").touch()
        (output_dir / "test_project_001.png").touch()

        loaded_result = operations.load_page_model(
            page_number=1,
            project_root=project_root,
            save_directory=str(output_dir),
            project_id="test_project",
        )
        assert loaded_result is not None
        loaded_page_model, _ = loaded_result
        loaded_page = loaded_page_model.page

        saved = operations.save_page(
            page=loaded_page,
            project_root=project_root,
            save_directory=str(output_dir),
            project_id="test_project",
        )
        assert saved is True

        with open(output_dir / "test_project_001.json", "r", encoding="utf-8") as f:
            saved_json = json.load(f)

        assert saved_json["provenance"]["ocr"]["models"] == []

    def test_can_load_page_success(self, operations, temp_dir):
        """Test checking if page can be loaded successfully."""
        # Create the necessary files
        project_root = temp_dir / "project"
        project_root.mkdir()

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        # Create valid JSON file
        json_file = output_dir / "project_001.json"
        json_data = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "source.png",
            "pages": [{"name": "test_page", "text": "Sample text"}],
        }
        with open(json_file, "w") as f:
            json.dump(json_data, f)

        load_info = operations.can_load_page(
            page_number=1,
            project_root=project_root,
            save_directory=str(temp_dir / "output"),
        )

        assert load_info.can_load is True
        assert load_info.json_filename == "project_001.json"
        assert load_info.file_prefix == "project_001"

    def test_can_load_page_not_found(self, operations, temp_dir):
        """Test checking if non-existent page can be loaded."""
        project_root = temp_dir / "project"
        project_root.mkdir()

        load_info = operations.can_load_page(
            page_number=1,
            project_root=project_root,
            save_directory=str(temp_dir / "output"),
        )

        assert load_info.can_load is False
        assert load_info.json_filename == "project_001.json"

    def test_can_load_page_with_project_relative_directory(self, operations, temp_dir):
        """Relative save_directory should resolve from project_root."""
        project_root = temp_dir / "project"
        output_dir = project_root / "local-data" / "labeled-ocr"
        output_dir.mkdir(parents=True)

        with open(output_dir / "project_001.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "source_lib": "doctr-pgdp-labeled",
                    "source_path": "source.png",
                    "pages": [{"name": "test_page", "text": "Sample text"}],
                },
                f,
            )

        load_info = operations.can_load_page(
            page_number=1,
            project_root=project_root,
            save_directory="local-data/labeled-ocr",
        )

        assert load_info.can_load is True
        assert load_info.json_path == output_dir / "project_001.json"

    def test_normalize_ground_truth_entries(self, operations):
        """Test normalizing ground truth entries."""
        # This test is now in test_ground_truth.py for ProjectState
        pass

    @pytest.mark.asyncio
    async def test_load_ground_truth_map_success(self, operations, temp_dir):
        """Test loading ground truth map successfully."""
        # This test is now in test_ground_truth.py for ProjectState
        pass

    @pytest.mark.asyncio
    async def test_load_ground_truth_map_not_found(self, operations, temp_dir):
        """Test loading ground truth map when file doesn't exist."""
        # This test is now in test_ground_truth.py for ProjectState
        pass

    @pytest.mark.parametrize(
        "name,expected_key",
        [
            ("001.png", "001.png"),
            ("001.PNG", "001.png"),  # Lowercase lookup
            ("001", "001"),  # No extension
            ("002.jpg", "002.jpg"),
            ("003", "003"),  # Extension added during normalization
        ],
    )
    def test_find_ground_truth_text(self, operations, name, expected_key):
        """Test finding ground truth text with various name formats."""
        # This test is now in test_ground_truth.py for ProjectState
        pass

    def test_find_ground_truth_text_empty_name(self, operations):
        """Test finding ground truth text with empty name."""
        # This test is now in test_ground_truth.py for ProjectState
        pass

    def test_find_ground_truth_text_no_match(self, operations):
        """Test finding ground truth text with no match."""
        # This test is now in test_ground_truth.py for ProjectState
        pass

    def test_refine_all_bboxes_success(self, operations):
        """Test successful bbox refinement."""
        # Create a mock page
        mock_page = MagicMock(spec=Page)
        mock_page.refine_bounding_boxes = MagicMock()
        mock_page.refresh_page_images = MagicMock()

        # Call refine_all_bboxes
        result = operations.refine_all_bboxes(mock_page, padding_px=2)

        # Verify the method was called correctly
        assert result is True
        mock_page.refine_bounding_boxes.assert_called_once_with(padding_px=2)
        mock_page.refresh_page_images.assert_called_once()

    def test_refine_all_bboxes_no_refresh_method(self, operations):
        """Test bbox refinement when page has no refresh_page_images method."""
        # Create a mock page without refresh_page_images
        mock_page = MagicMock(spec=Page)
        mock_page.refine_bounding_boxes = MagicMock()
        # Don't add refresh_page_images method

        # Call refine_all_bboxes
        result = operations.refine_all_bboxes(mock_page, padding_px=3)

        # Verify the method was called correctly
        assert result is True
        mock_page.refine_bounding_boxes.assert_called_once_with(padding_px=3)
        # refresh_page_images should not be called since it doesn't exist

    def test_refine_all_bboxes_refine_fails(self, operations):
        """Test bbox refinement when refine_bounding_boxes raises an exception."""
        # Create a mock page that raises an exception
        mock_page = MagicMock(spec=Page)
        mock_page.refine_bounding_boxes = MagicMock(
            side_effect=Exception("Refine failed")
        )

        # Call refine_all_bboxes
        result = operations.refine_all_bboxes(mock_page)

        # Verify the result is False
        assert result is False
        mock_page.refine_bounding_boxes.assert_called_once_with(padding_px=2)

    def test_expand_and_refine_all_bboxes_success(self, operations):
        """Test successful bbox expansion and refinement."""
        # Create a mock page with mock blocks and words
        mock_word = MagicMock()
        mock_word.crop_bottom = MagicMock()
        mock_word.expand_to_content = MagicMock()

        mock_block = MagicMock()
        mock_block.words = [mock_word]

        mock_page = MagicMock(spec=Page)
        mock_page.blocks = [mock_block]
        mock_page.refine_bounding_boxes = MagicMock()
        mock_page.refresh_page_images = MagicMock()

        # Call expand_and_refine_all_bboxes
        result = operations.expand_and_refine_all_bboxes(mock_page, padding_px=2)

        # Verify the methods were called correctly
        assert result is True
        mock_word.crop_bottom.assert_called_once()
        mock_word.expand_to_content.assert_called_once()
        mock_page.refine_bounding_boxes.assert_called_once_with(padding_px=2)
        mock_page.refresh_page_images.assert_called_once()

    def test_expand_and_refine_all_bboxes_no_methods(self, operations):
        """Test bbox expansion and refinement when words have no crop/expand methods."""
        # Create a mock page with words that don't have the methods
        mock_word = MagicMock()
        # Don't add crop_bottom or expand_to_content methods

        mock_block = MagicMock()
        mock_block.words = [mock_word]

        mock_page = MagicMock(spec=Page)
        mock_page.blocks = [mock_block]
        mock_page.refine_bounding_boxes = MagicMock()
        mock_page.refresh_page_images = MagicMock()

        # Call expand_and_refine_all_bboxes
        result = operations.expand_and_refine_all_bboxes(mock_page, padding_px=3)

        # Verify the method was called correctly
        assert result is True
        # crop_bottom and expand_to_content should not be called since they don't exist
        mock_page.refine_bounding_boxes.assert_called_once_with(padding_px=3)
        mock_page.refresh_page_images.assert_called_once()

    def test_expand_and_refine_all_bboxes_refine_fails(self, operations):
        """Test bbox expansion and refinement when refine_bounding_boxes raises an exception."""
        # Create a mock page that raises an exception
        mock_word = MagicMock()
        mock_word.crop_bottom = MagicMock()
        mock_word.expand_to_content = MagicMock()

        mock_block = MagicMock()
        mock_block.words = [mock_word]

        mock_page = MagicMock(spec=Page)
        mock_page.blocks = [mock_block]
        mock_page.refine_bounding_boxes = MagicMock(
            side_effect=Exception("Refine failed")
        )

        # Call expand_and_refine_all_bboxes
        result = operations.expand_and_refine_all_bboxes(mock_page)

        # Verify the result is False
        assert result is False
        mock_word.crop_bottom.assert_called_once()
        mock_word.expand_to_content.assert_called_once()
        mock_page.refine_bounding_boxes.assert_called_once_with(padding_px=2)

    @patch("pd_book_tools.ocr.doctr_support.get_default_doctr_predictor")
    @patch("pd_book_tools.ocr.document.Document.from_image_ocr_via_doctr")
    @patch("cv2.imread")
    def test_reset_ocr_success(
        self, mock_cv2_imread, mock_from_image_ocr, mock_get_predictor, temp_dir
    ):
        """Test successful OCR reset."""
        # Setup mocks
        mock_predictor = MagicMock()
        mock_get_predictor.return_value = mock_predictor

        mock_page = MagicMock(spec=Page)
        mock_page.name = "test_page"
        mock_page.text = "Fresh OCR text"
        mock_doc = MagicMock()
        mock_doc.pages = [mock_page]
        mock_from_image_ocr.return_value = mock_doc

        mock_cv2_imread.return_value = MagicMock()  # Mock image array

        operations = PageOperations()

        # Create test image
        image_path = temp_dir / "test.png"
        image_path.touch()

        # Reset OCR
        result_page = operations.reset_ocr(
            image_path=image_path, index=0, ground_truth_text="Test GT"
        )

        # Verify results
        assert result_page == mock_page
        mock_from_image_ocr.assert_called_once()
        mock_cv2_imread.assert_called_once_with(str(image_path))

    def test_reset_ocr_failure(self, operations, temp_dir):
        """Test OCR reset when parser fails."""
        # Create test image
        image_path = temp_dir / "test.png"
        image_path.touch()

        # Mock the page_parser to return None
        operations.page_parser = MagicMock(return_value=None)

        # Reset OCR should return None on failure
        result_page = operations.reset_ocr(image_path=image_path)

        assert result_page is None
        operations.page_parser.assert_called_once()

    @patch("pd_book_tools.ocr.doctr_support.get_default_doctr_predictor")
    def test_reset_ocr_exception_handling(
        self, mock_get_predictor, operations, temp_dir
    ):
        """Test OCR reset exception handling."""
        # Setup mock to raise exception
        mock_get_predictor.side_effect = Exception("OCR processing failed")

        # Create test image
        image_path = temp_dir / "test.png"
        image_path.touch()

        # Reset OCR should handle exception and return None
        result_page = operations.reset_ocr(image_path=image_path)

        assert result_page is None
