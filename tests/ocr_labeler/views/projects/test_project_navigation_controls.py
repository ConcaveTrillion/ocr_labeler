"""Tests for project-level navigation controls."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import ocr_labeler.views.projects.project_navigation_controls as nav_module
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

    def test_bind_from_safe_does_not_raise_and_notifies_once(self, monkeypatch):
        """Binding setup failures should be non-fatal and user-notified once."""
        controls = ProjectNavigationControls(
            viewmodel=Mock(),
            on_prev=Mock(),
            on_next=Mock(),
            on_goto=Mock(),
        )

        def failing_bind_from(*_args, **_kwargs):
            raise RuntimeError("bind failed")

        monkeypatch.setattr(nav_module.binding, "bind_from", failing_bind_from)
        notify_mock = MagicMock()
        monkeypatch.setattr(controls, "_notify", notify_mock)

        controls._bind_from_safe(
            object(),
            "disable",
            object(),
            "busy",
            key="nav-bind-key",
            message="nav binding failed",
        )
        controls._bind_from_safe(
            object(),
            "disable",
            object(),
            "busy",
            key="nav-bind-key",
            message="nav binding failed",
        )

        notify_mock.assert_called_once_with("nav binding failed", "warning")
