"""Tests for PageOperations.load_page functionality."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from ocr_labeler.operations.ocr import PageOperations


class TestLoadPage:
    """Test PageOperations.load_page functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.page_operations = PageOperations()
        self.project_root = Path("/test/project")

    def test_load_page_file_exists_valid_structure(self, tmp_path):
        """Test load_page when file exists and has valid structure."""
        # Create a valid JSON file
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        json_file = save_dir / "test_project_001.json"
        json_data = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "test_image.png",
            "pages": [{"type": "Page", "items": [], "width": 800, "height": 600}],
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f)

        # Mock Page.from_dict to avoid dependency on actual Page implementation
        with patch(
            "ocr_labeler.operations.ocr.page_operations.Page"
        ) as mock_page_class:
            mock_page = Mock()
            mock_page_class.from_dict.return_value = mock_page

            # Test load_page
            result = self.page_operations.load_page(
                page_number=1,
                project_root=self.project_root,
                save_directory=str(save_dir),
                project_id="test_project",
            )

            assert result is mock_page
            mock_page_class.from_dict.assert_called_once_with(json_data["pages"][0])

    def test_load_page_file_not_exists(self, tmp_path):
        """Test load_page when JSON file doesn't exist."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        result = self.page_operations.load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result is None

    def test_load_page_directory_not_exists(self, tmp_path):
        """Test load_page when save directory doesn't exist."""
        save_dir = tmp_path / "nonexistent_directory"

        result = self.page_operations.load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result is None

    def test_load_page_invalid_json_structure(self, tmp_path):
        """Test load_page when JSON file has invalid structure."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        json_file = save_dir / "test_project_001.json"

        # Create JSON without required "pages" key
        invalid_json_data = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "test_image.png",
            # Missing "pages" key
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(invalid_json_data, f)

        result = self.page_operations.load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result is None

    def test_load_page_corrupted_json(self, tmp_path):
        """Test load_page when JSON file is corrupted/unparseable."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        json_file = save_dir / "test_project_001.json"

        # Write invalid JSON
        with open(json_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json structure")

        result = self.page_operations.load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result is None

    def test_load_page_generates_project_id_from_root(self, tmp_path):
        """Test that project ID is generated from project_root when not provided."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        # Set project_root with a specific name
        project_root = Path("my_book_project")

        # Create valid JSON file with expected filename
        json_file = save_dir / "my_book_project_002.json"
        json_data = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "test_image.png",
            "pages": [{"type": "Page", "items": []}],
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f)

        # Mock Page.from_dict
        with patch(
            "ocr_labeler.operations.ocr.page_operations.Page"
        ) as mock_page_class:
            mock_page = Mock()
            mock_page_class.from_dict.return_value = mock_page

            # Test without providing project_id
            result = self.page_operations.load_page(
                page_number=2,
                project_root=project_root,
                save_directory=str(save_dir),
                # No project_id provided
            )

            assert result is mock_page
            mock_page_class.from_dict.assert_called_once_with(json_data["pages"][0])

    def test_load_page_empty_pages_list(self, tmp_path):
        """Test load_page when pages list is empty."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        json_file = save_dir / "test_project_001.json"
        json_data = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "test_image.png",
            "pages": [],  # Empty pages list
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f)

        result = self.page_operations.load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result is None

    def test_load_page_pages_not_list(self, tmp_path):
        """Test load_page when pages value is not a list."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        json_file = save_dir / "test_project_001.json"
        json_data = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "test_image.png",
            "pages": "not a list",  # Invalid type
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f)

        result = self.page_operations.load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result is None
