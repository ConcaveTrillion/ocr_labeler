"""Tests for main view components."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from nicegui.testing import User

from ocr_labeler import app
from ocr_labeler.state import AppState
from ocr_labeler.viewmodels.main_view_model import MainViewModel
from ocr_labeler.views.main_view import LabelerView


class TestMainView:
    """Test MainView functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.app_state = AppState()
        self.main_view_model = MainViewModel(self.app_state)
        self.main_view = LabelerView(self.main_view_model)

    def test_main_view_initialization(self):
        """Test that MainView initializes correctly."""
        assert self.main_view.viewmodel == self.main_view_model
        assert self.main_view.header_bar is None
        assert self.main_view.project_view is None
        assert self.main_view._no_project_placeholder is None
        assert self.main_view._global_loading is None

    @patch("ocr_labeler.views.main_view.ui")
    def test_project_view_has_load_page(self, mock_ui):
        """Test that ProjectView has load_page functionality."""
        from ocr_labeler.views.projects.project_view import ProjectView

        # Mock the required UI components
        mock_ui.page = Mock()
        mock_ui.spinner = Mock()
        mock_ui.column = Mock()
        mock_ui.icon = Mock()
        mock_ui.label = Mock()

        # Create a project view with the viewmodel
        project_view = ProjectView(self.main_view_model.project_state_viewmodel)

        # The project view should have load_page functionality
        assert hasattr(project_view, "_load_page_async")


@pytest.mark.module_under_test(app)
async def test_main_view_placeholder_display(user: User):
    """Test that the main view displays the no project placeholder correctly."""
    # Create the app instance and set up routes
    from pathlib import Path

    labeler = app.NiceGuiLabeler(project_root=Path("."))
    labeler.create_routes()

    # Open the page and check that it loads without errors
    await user.open("/")
    # With User fixture, we can check that the page opened successfully
    # The User fixture is primarily for simulating user interactions
    await user.should_see("No Project Loaded")
