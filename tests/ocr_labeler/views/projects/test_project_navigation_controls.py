"""Tests for project-level navigation controls."""

from __future__ import annotations

from unittest.mock import Mock

from ocr_labeler.views.projects.project_navigation_controls import (
    ProjectNavigationControls,
)


class TestProjectNavigationControls:
    """Test ProjectNavigationControls functionality."""

    def test_navigation_controls_initialization(self):
        """Test that ProjectNavigationControls initializes correctly."""
        mock_viewmodel = Mock()
        mock_on_prev = Mock()
        mock_on_next = Mock()
        mock_on_goto = Mock()

        controls = ProjectNavigationControls(
            viewmodel=mock_viewmodel,
            on_prev=mock_on_prev,
            on_next=mock_on_next,
            on_goto=mock_on_goto,
        )

        assert controls.viewmodel == mock_viewmodel
        assert controls._on_prev == mock_on_prev
        assert controls._on_next == mock_on_next
        assert controls._on_goto == mock_on_goto
        assert controls.page_input is None
        assert controls.page_total is None

    def test_navigation_controls_initialization_required_callbacks_only(self):
        """Test that ProjectNavigationControls initializes with required callbacks."""
        mock_viewmodel = Mock()
        mock_on_prev = Mock()
        mock_on_next = Mock()
        mock_on_goto = Mock()

        controls = ProjectNavigationControls(
            viewmodel=mock_viewmodel,
            on_prev=mock_on_prev,
            on_next=mock_on_next,
            on_goto=mock_on_goto,
        )

        assert controls.viewmodel == mock_viewmodel
        assert controls._on_prev == mock_on_prev
        assert controls._on_next == mock_on_next
        assert controls._on_goto == mock_on_goto
