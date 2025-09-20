"""Tests for main view components."""

from __future__ import annotations

from unittest.mock import Mock, patch

from ocr_labeler.state import AppState
from ocr_labeler.views.main_view import LabelerView


class TestMainView:
    """Test MainView functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app_state = AppState()
        self.main_view = LabelerView(self.app_state)

    def test_main_view_initialization(self):
        """Test that MainView initializes correctly."""
        assert self.main_view.state == self.app_state
        assert self.main_view.header_bar is None
        assert self.main_view.project_view is None
        assert self.main_view._no_project_placeholder is None
        assert self.main_view._global_loading is None

    @patch("ocr_labeler.views.main_view.ui")
    def test_project_view_has_load_page(self, mock_ui):
        """Test that ProjectView has load_page functionality."""
        from ocr_labeler.views.project_view import ProjectView

        # Mock the required UI components
        mock_ui.page = Mock()
        mock_ui.spinner = Mock()
        mock_ui.column = Mock()
        mock_ui.icon = Mock()
        mock_ui.label = Mock()

        # Create a project view
        project_view = ProjectView(self.app_state)

        # The project view should have load_page functionality
        assert hasattr(project_view, "_load_page_async")
