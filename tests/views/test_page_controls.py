"""Tests for view components."""

from __future__ import annotations

from unittest.mock import Mock

from ocr_labeler.views.page_controls import PageControls


class TestPageControls:
    """Test PageControls functionality."""

    def test_page_controls_initialization_with_load_callback(self):
        """Test that PageControls initializes correctly with load callback."""
        mock_state = Mock()
        mock_on_prev = Mock()
        mock_on_next = Mock()
        mock_on_goto = Mock()
        mock_on_save = Mock()
        mock_on_load = Mock()

        controls = PageControls(
            state=mock_state,
            on_prev=mock_on_prev,
            on_next=mock_on_next,
            on_goto=mock_on_goto,
            on_save_page=mock_on_save,
            on_load_page=mock_on_load,
        )

        assert controls.state == mock_state
        assert controls._on_prev == mock_on_prev
        assert controls._on_next == mock_on_next
        assert controls._on_goto == mock_on_goto
        assert controls._on_save_page == mock_on_save
        assert controls._on_load_page == mock_on_load

    def test_page_controls_initialization_without_load_callback(self):
        """Test that PageControls initializes correctly without load callback."""
        mock_state = Mock()
        mock_on_prev = Mock()
        mock_on_next = Mock()
        mock_on_goto = Mock()
        mock_on_save = Mock()

        controls = PageControls(
            state=mock_state,
            on_prev=mock_on_prev,
            on_next=mock_on_next,
            on_goto=mock_on_goto,
            on_save_page=mock_on_save,
            # No on_load_page provided
        )

        assert controls.state == mock_state
        assert controls._on_prev == mock_on_prev
        assert controls._on_next == mock_on_next
        assert controls._on_goto == mock_on_goto
        assert controls._on_save_page == mock_on_save
        assert controls._on_load_page is None

    def test_page_controls_initialization_without_callbacks(self):
        """Test that PageControls initializes correctly with minimal callbacks."""
        mock_state = Mock()
        mock_on_prev = Mock()
        mock_on_next = Mock()
        mock_on_goto = Mock()

        controls = PageControls(
            state=mock_state,
            on_prev=mock_on_prev,
            on_next=mock_on_next,
            on_goto=mock_on_goto,
            # No save or load callbacks
        )

        assert controls.state == mock_state
        assert controls._on_prev == mock_on_prev
        assert controls._on_next == mock_on_next
        assert controls._on_goto == mock_on_goto
        assert controls._on_save_page is None
        assert controls._on_load_page is None
