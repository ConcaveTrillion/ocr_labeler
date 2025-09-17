"""Tests for PageOperations.can_load_page functionality."""

import json
from pathlib import Path

from ocr_labeler.state.operations import PageOperations


class TestCanLoadPage:
    """Test PageOperations.can_load_page functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.page_operations = PageOperations()
        self.project_root = Path("/test/project")

    def test_can_load_page_file_exists_valid_structure(self, tmp_path):
        """Test can_load_page when file exists and has valid structure."""
        # Create a valid JSON file
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        json_file = save_dir / "test_project_001.json"
        json_data = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "test_image.png",
            "pages": [{"type": "Page", "items": []}],
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f)

        # Test can_load_page
        result = self.page_operations.can_load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result.can_load is True
        assert result.json_filename == "test_project_001.json"
        assert result.json_path == json_file
        assert result.file_prefix == "test_project_001"

    def test_can_load_page_file_not_exists(self, tmp_path):
        """Test can_load_page when JSON file doesn't exist."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        result = self.page_operations.can_load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result.can_load is False
        assert result.json_filename == "test_project_001.json"
        assert result.json_path == save_dir / "test_project_001.json"
        assert result.file_prefix == "test_project_001"

    def test_can_load_page_directory_not_exists(self, tmp_path):
        """Test can_load_page when save directory doesn't exist."""
        save_dir = tmp_path / "nonexistent_directory"

        result = self.page_operations.can_load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result.can_load is False
        assert result.json_filename == "test_project_001.json"
        assert result.json_path == save_dir / "test_project_001.json"
        assert result.file_prefix == "test_project_001"

    def test_can_load_page_invalid_json_structure(self, tmp_path):
        """Test can_load_page when JSON file has invalid structure."""
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

        result = self.page_operations.can_load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result.can_load is False
        assert result.json_filename == "test_project_001.json"
        assert result.json_path == json_file
        assert result.file_prefix == "test_project_001"

    def test_can_load_page_corrupted_json(self, tmp_path):
        """Test can_load_page when JSON file is corrupted/unparseable."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        json_file = save_dir / "test_project_001.json"

        # Write invalid JSON
        with open(json_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json structure")

        result = self.page_operations.can_load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result.can_load is False
        assert result.json_filename == "test_project_001.json"
        assert result.json_path == json_file
        assert result.file_prefix == "test_project_001"

    def test_can_load_page_generates_project_id_from_root(self, tmp_path):
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

        # Test without providing project_id
        result = self.page_operations.can_load_page(
            page_number=2,
            project_root=project_root,
            save_directory=str(save_dir),
            # No project_id provided
        )

        assert result.can_load is True
        assert result.json_filename == "my_book_project_002.json"
        assert result.json_path == json_file
        assert result.file_prefix == "my_book_project_002"

    def test_can_load_page_different_page_numbers(self, tmp_path):
        """Test can_load_page with different page numbers."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        # Create files for pages 1, 5, and 10
        for page_num in [1, 5, 10]:
            json_file = save_dir / f"test_project_{page_num:03d}.json"
            json_data = {
                "source_lib": "doctr-pgdp-labeled",
                "source_path": f"test_image_{page_num}.png",
                "pages": [{"type": "Page", "items": []}],
            }

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f)

        # Test existing pages
        for page_num in [1, 5, 10]:
            result = self.page_operations.can_load_page(
                page_number=page_num,
                project_root=self.project_root,
                save_directory=str(save_dir),
                project_id="test_project",
            )

            assert result.can_load is True
            assert result.json_filename == f"test_project_{page_num:03d}.json"
            assert result.file_prefix == f"test_project_{page_num:03d}"

        # Test non-existing pages
        for page_num in [2, 3, 4, 6, 7, 8, 9, 11]:
            result = self.page_operations.can_load_page(
                page_number=page_num,
                project_root=self.project_root,
                save_directory=str(save_dir),
                project_id="test_project",
            )

            assert result.can_load is False
            assert result.json_filename == f"test_project_{page_num:03d}.json"
            assert result.file_prefix == f"test_project_{page_num:03d}"

    def test_can_load_page_exception_handling(self, tmp_path):
        """Test can_load_page exception handling with invalid inputs."""
        # This should not crash even with problematic inputs
        result = self.page_operations.can_load_page(
            page_number=-1,  # Invalid page number
            project_root=Path("/nonexistent/path"),
            save_directory=str(tmp_path / "save_test"),
            project_id="test_project",
        )

        # Should still return a valid PageLoadInfo object
        assert result.can_load is False
        assert (
            result.json_filename == "test_project_-01.json"
        )  # Note: handles negative numbers (2-digit formatting)
        assert isinstance(result.json_path, Path)
        assert result.file_prefix == "test_project_-01"

    def test_can_load_page_custom_save_directory(self, tmp_path):
        """Test can_load_page with custom save directory."""
        custom_dir = tmp_path / "custom" / "save" / "location"
        custom_dir.mkdir(parents=True)

        # Create valid JSON file
        json_file = custom_dir / "test_project_003.json"
        json_data = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "test_image.png",
            "pages": [{"type": "Page", "items": []}],
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f)

        result = self.page_operations.can_load_page(
            page_number=3,
            project_root=self.project_root,
            save_directory=str(custom_dir),
            project_id="test_project",
        )

        assert result.can_load is True
        assert result.json_filename == "test_project_003.json"
        assert result.json_path == json_file
        assert result.file_prefix == "test_project_003"

    def test_can_load_page_json_is_not_dict(self, tmp_path):
        """Test can_load_page when JSON file contains non-dict data."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        json_file = save_dir / "test_project_001.json"

        # Write JSON that's a list instead of dict
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(["not", "a", "dict"], f)

        result = self.page_operations.can_load_page(
            page_number=1,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result.can_load is False
        assert result.json_filename == "test_project_001.json"
        assert result.json_path == json_file
        assert result.file_prefix == "test_project_001"

    def test_can_load_page_zero_page_number(self, tmp_path):
        """Test can_load_page with page number 0 (edge case)."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        result = self.page_operations.can_load_page(
            page_number=0,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result.can_load is False
        assert result.json_filename == "test_project_000.json"
        assert result.json_path == save_dir / "test_project_000.json"
        assert result.file_prefix == "test_project_000"

    def test_can_load_page_large_page_number(self, tmp_path):
        """Test can_load_page with large page numbers."""
        save_dir = tmp_path / "save_test"
        save_dir.mkdir(parents=True)

        # Test with page number 999
        json_file = save_dir / "test_project_999.json"
        json_data = {
            "source_lib": "doctr-pgdp-labeled",
            "source_path": "test_image.png",
            "pages": [{"type": "Page", "items": []}],
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f)

        result = self.page_operations.can_load_page(
            page_number=999,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result.can_load is True
        assert result.json_filename == "test_project_999.json"
        assert result.json_path == json_file
        assert result.file_prefix == "test_project_999"
