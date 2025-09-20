from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

from ocr_labeler.state.project_state import ProjectState


def test_project_state_initialization():
    """Test that ProjectState initializes correctly."""
    state = ProjectState()
    assert state.project is not None
    assert state.current_page_index == 0
    assert state.current_page() is None  # No pages loaded yet
    assert state.is_loading is False
    assert state.on_change == []


def test_project_state_notification():
    """Test that ProjectState notification system works."""
    state = ProjectState()
    calls = []
    state.on_change.append(lambda: calls.append("notified"))
    state.notify()
    assert calls == ["notified"]


def test_project_state_delegation():
    """Test that ProjectState methods delegate correctly."""
    state = ProjectState()

    # Test navigation methods exist and can be called
    # (These won't do much without a loaded project, but they shouldn't crash)
    state.next_page()
    state.prev_page()
    state.goto_page_number(1)

    # Test current page returns None when no project loaded
    assert state.current_page() is None


def test_load_current_page_success(tmp_path):
    """Test load_current_page when file exists and loads successfully."""
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

    # Mock Page.from_dict and the page operations
    with patch("ocr_labeler.state.operations.page_operations.Page") as mock_page_class:
        mock_page = Mock()
        mock_page_class.from_dict.return_value = mock_page

        # Set up project state
        state = ProjectState()
        state.project_root = Path("/test/project")
        state.current_page_index = 0

        # Mock the project.pages list
        mock_project = Mock()
        mock_project.pages = [None]  # Initially None, should be replaced
        state.project = mock_project

        # Test load_current_page
        result = state.load_current_page(
            save_directory=str(save_dir),
            project_id="test_project",
        )

        assert result is True
        assert state.project.pages[0] is mock_page
        mock_page_class.from_dict.assert_called_once_with(json_data["pages"][0])


def test_load_current_page_no_saved_file(tmp_path):
    """Test load_current_page when no saved file exists."""
    save_dir = tmp_path / "save_test"
    save_dir.mkdir(parents=True)

    state = ProjectState()
    state.project_root = Path("/test/project")
    state.current_page_index = 0

    result = state.load_current_page(
        save_directory=str(save_dir),
        project_id="test_project",
    )

    assert result is False


def test_load_current_page_invalid_index(tmp_path):
    """Test load_current_page when current_page_index is out of range."""
    save_dir = tmp_path / "save_test"
    save_dir.mkdir(parents=True)

    state = ProjectState()
    state.project_root = Path("/test/project")
    state.current_page_index = 5  # Out of range

    # Mock project with only 3 pages
    mock_project = Mock()
    mock_project.pages = [Mock(), Mock(), Mock()]
    state.project = mock_project

    result = state.load_current_page(
        save_directory=str(save_dir),
        project_id="test_project",
    )

    assert result is False


def test_load_current_page_negative_index(tmp_path):
    """Test load_current_page when current_page_index is negative."""
    save_dir = tmp_path / "save_test"
    save_dir.mkdir(parents=True)

    state = ProjectState()
    state.project_root = Path("/test/project")
    state.current_page_index = -1

    result = state.load_current_page(
        save_directory=str(save_dir),
        project_id="test_project",
    )

    assert result is False


def test_load_current_page_generates_project_id_from_root(tmp_path):
    """Test that project ID is generated from project_root when not provided."""
    save_dir = tmp_path / "save_test"
    save_dir.mkdir(parents=True)

    # Create valid JSON file with expected filename
    json_file = save_dir / "my_book_project_001.json"
    json_data = {
        "source_lib": "doctr-pgdp-labeled",
        "source_path": "test_image.png",
        "pages": [{"type": "Page", "items": []}],
    }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f)

    # Mock Page.from_dict
    with patch("ocr_labeler.state.operations.page_operations.Page") as mock_page_class:
        mock_page = Mock()
        mock_page_class.from_dict.return_value = mock_page

        # Set up project state with specific project root
        state = ProjectState()
        state.project_root = Path("my_book_project")
        state.current_page_index = 0

        # Mock the project.pages list
        mock_project = Mock()
        mock_project.pages = [None]
        state.project = mock_project

        # Test without providing project_id
        result = state.load_current_page(
            save_directory=str(save_dir),
            # No project_id provided
        )

        assert result is True
        assert state.project.pages[0] is mock_page
