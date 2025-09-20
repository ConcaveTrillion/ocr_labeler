"""
Basic boilerplate tests for AppState.

This file contains minimal bare-bones tests for the AppState class.
More comprehensive tests can be found in tests/test_app_state.py.
"""

from pathlib import Path

import pytest

from ocr_labeler.state.app_state import AppState


class TestAppState:
    """Basic tests for AppState functionality."""

    def test_app_state_initialization(self):
        """Test that AppState can be instantiated with default values."""
        state = AppState()

        # Check basic initialization
        assert state.base_projects_root is None
        assert state.monospace_font_name == "monospace"
        assert state.monospace_font_path is None
        assert state.is_project_loading is False
        assert state.on_change == []

        # Check that project_state is initialized
        assert state.project_state is not None

        # Check reactive data structures are initialized
        assert isinstance(state.available_projects, dict)
        assert isinstance(state.project_keys, list)
        assert state.selected_project_key is None or isinstance(
            state.selected_project_key, str
        )

    def test_notify_method(self):
        """Test that notify method works without callback."""
        state = AppState()

        # Should not raise when no callback is set
        state.notify()

        # Test with callback
        called = []
        state.on_change.append(lambda: called.append(True))
        state.notify()

        assert len(called) == 1

    def test_is_loading_property(self):
        """Test that is_loading property delegates to project_state."""
        state = AppState()

        # Initially should be False
        assert state.is_loading is False

        # Setting should delegate to project_state
        state.is_loading = True
        assert state.project_state.is_loading is True
        assert state.is_loading is True

    @pytest.mark.asyncio
    async def test_load_project_nonexistent_path(self):
        """Test that loading a nonexistent project raises FileNotFoundError."""
        state = AppState()
        nonexistent_path = Path("/nonexistent/path/to/project")

        with pytest.raises(FileNotFoundError):
            await state.load_project(nonexistent_path)

    def test_selected_project_path(self, tmp_path):
        """Test selected_project_path method returns correct path or None."""
        state = AppState()

        # Clear any auto-discovered projects for clean test
        state.available_projects = {}
        state.selected_project_key = None

        # Should return None when no project selected
        assert state.selected_project_path() is None

        # Use pytest's tmp_path for test project
        test_project_path = tmp_path / "test_project"
        test_project_path.mkdir()

        state.available_projects = {"test_project": test_project_path}
        state.selected_project_key = "test_project"

        assert state.selected_project_path() == test_project_path

        # Should return None for unknown key
        state.selected_project_key = "unknown_project"
        assert state.selected_project_path() is None
