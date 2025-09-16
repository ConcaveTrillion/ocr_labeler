"""Tests for save_page functionality in PageOperations and ProjectState integration."""

import json
from pathlib import Path
from unittest.mock import Mock

from pd_book_tools.ocr.page import Page

from ocr_labeler.state.operations import PageOperations
from ocr_labeler.state.project_state import ProjectState


class TestPageOperations:
    """Test PageOperations.save_page functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.page_operations = PageOperations()
        self.project_root = Path("/test/project")

    def test_save_page_with_valid_page(self, tmp_path):
        """Test saving a valid page."""
        # Create a mock page with required attributes
        mock_page = Mock(spec=Page)
        mock_page.index = 0
        mock_page.image_path = Path("/test/project/test_image.png")
        mock_page.to_dict.return_value = {
            "type": "Page",
            "width": 800,
            "height": 600,
            "page_index": 0,
            "items": [],
        }

        # Create a dummy source image
        source_image = tmp_path / "source_image.png"
        source_image.write_bytes(b"dummy image data")
        mock_page.image_path = source_image

        # Save to temp directory
        save_dir = tmp_path / "save_test"
        result = self.page_operations.save_page(
            page=mock_page,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result is True

        # Check image file was copied
        expected_image = save_dir / "test_project_001.png"
        assert expected_image.exists()
        assert expected_image.read_bytes() == b"dummy image data"

        # Check JSON file was created
        expected_json = save_dir / "test_project_001.json"
        assert expected_json.exists()

        with open(expected_json, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        assert json_data["source_lib"] == "doctr-pgdp-labeled"
        assert json_data["source_path"] == "source_image.png"
        assert len(json_data["pages"]) == 1
        assert json_data["pages"][0]["type"] == "Page"

    def test_save_page_missing_image_path(self, tmp_path):
        """Test save_page when page has no image_path."""
        mock_page = Mock(spec=Page)
        mock_page.index = 0
        mock_page.image_path = None

        result = self.page_operations.save_page(
            page=mock_page,
            project_root=self.project_root,
            save_directory=str(tmp_path / "save_test"),
        )

        assert result is False

    def test_save_page_generates_project_id_from_root(self, tmp_path):
        """Test that project ID is generated from project_root when not provided."""
        # Create a mock page
        mock_page = Mock(spec=Page)
        mock_page.index = 1

        # Create a dummy source image
        source_image = tmp_path / "source_image.jpg"
        source_image.write_bytes(b"dummy image data")
        mock_page.image_path = source_image
        mock_page.to_dict.return_value = {"type": "Page", "items": []}

        # Set project_root with a specific name
        project_root = Path("my_book_project")

        save_dir = tmp_path / "save_test"
        result = self.page_operations.save_page(
            page=mock_page,
            project_root=project_root,
            save_directory=str(save_dir),
        )

        assert result is True

        # Check files were created with project name from project_root
        expected_image = save_dir / "my_book_project_002.jpg"
        expected_json = save_dir / "my_book_project_002.json"

        assert expected_image.exists()
        assert expected_json.exists()

    def test_save_page_handles_different_image_extensions(self, tmp_path):
        """Test that different image extensions are preserved."""
        for ext in [".png", ".jpg", ".jpeg"]:
            mock_page = Mock(spec=Page)
            mock_page.index = 0

            source_image = tmp_path / f"test{ext}"
            source_image.write_bytes(b"image data")
            mock_page.image_path = source_image
            mock_page.to_dict.return_value = {"type": "Page", "items": []}

            save_dir = tmp_path / f"save_test_{ext[1:]}"
            result = self.page_operations.save_page(
                page=mock_page,
                project_root=self.project_root,
                save_directory=str(save_dir),
                project_id="test",
            )

            assert result is True
            expected_image = save_dir / f"test_001{ext}"
            assert expected_image.exists()

    def test_save_page_creates_directory(self, tmp_path):
        """Test that save_page creates the save directory if it doesn't exist."""
        mock_page = Mock(spec=Page)
        mock_page.index = 0

        source_image = tmp_path / "source.png"
        source_image.write_bytes(b"data")
        mock_page.image_path = source_image
        mock_page.to_dict.return_value = {"type": "Page", "items": []}

        # Use a non-existent nested directory
        save_dir = tmp_path / "nested" / "deep" / "directory"

        result = self.page_operations.save_page(
            page=mock_page,
            project_root=self.project_root,
            save_directory=str(save_dir),
            project_id="test",
        )

        assert result is True
        assert save_dir.exists()
        assert (save_dir / "test_001.png").exists()
        assert (save_dir / "test_001.json").exists()


class TestProjectStateIntegration:
    """Test ProjectState integration with PageOperations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.project_state = ProjectState()
        self.project_state.project_root = Path("/test/project")

    def test_save_current_page_with_valid_page(self, tmp_path):
        """Test saving current page via ProjectState convenience method."""
        # Create a mock page
        mock_page = Mock(spec=Page)
        mock_page.index = 0
        mock_page.to_dict.return_value = {"type": "Page", "items": []}

        # Create a dummy source image
        source_image = tmp_path / "source_image.png"
        source_image.write_bytes(b"dummy image data")
        mock_page.image_path = source_image

        # Mock the current_page method to return our test page
        self.project_state.current_page = lambda: mock_page

        # Save to temp directory using convenience method
        save_dir = tmp_path / "save_test"
        result = self.project_state.save_current_page(
            save_directory=str(save_dir), project_id="test_project"
        )

        assert result is True

        # Check files were created
        expected_image = save_dir / "test_project_001.png"
        expected_json = save_dir / "test_project_001.json"
        assert expected_image.exists()
        assert expected_json.exists()

    def test_save_current_page_no_current_page(self, tmp_path):
        """Test save_current_page when no current page is available."""
        # Mock current_page to return None
        self.project_state.current_page = lambda: None

        result = self.project_state.save_current_page(
            save_directory=str(tmp_path / "save_test")
        )

        assert result is False
