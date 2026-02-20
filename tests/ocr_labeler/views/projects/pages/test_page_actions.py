"""Tests for page-level actions component."""

from __future__ import annotations

from unittest.mock import Mock

from ocr_labeler.views.projects.pages.page_actions import PageActions


class TestPageActions:
    """Test PageActions functionality."""

    def test_page_actions_initialization_with_callbacks(self):
        """PageActions stores page action callbacks independently."""
        mock_project_viewmodel = Mock()
        mock_page_viewmodel = Mock()
        mock_on_save = Mock()
        mock_on_load = Mock()
        mock_on_refine = Mock()
        mock_on_expand_refine = Mock()
        mock_on_reload = Mock()

        controls = PageActions(
            project_viewmodel=mock_project_viewmodel,
            page_viewmodel=mock_page_viewmodel,
            on_save_page=mock_on_save,
            on_load_page=mock_on_load,
            on_refine_bboxes=mock_on_refine,
            on_expand_refine_bboxes=mock_on_expand_refine,
            on_reload_ocr=mock_on_reload,
        )

        assert controls.project_viewmodel == mock_project_viewmodel
        assert controls.page_viewmodel == mock_page_viewmodel
        assert controls._on_save_page == mock_on_save
        assert controls._on_load_page == mock_on_load
        assert controls._on_refine_bboxes == mock_on_refine
        assert controls._on_expand_refine_bboxes == mock_on_expand_refine
        assert controls._on_reload_ocr == mock_on_reload
        assert controls.page_name_box is None
        assert controls.page_source_label is None
        assert controls.page_source_tooltip is None

    def test_page_actions_initialization_without_callbacks(self):
        """PageActions supports optional page actions."""
        controls = PageActions(project_viewmodel=Mock(), page_viewmodel=Mock())

        assert controls._on_save_page is None
        assert controls._on_load_page is None
        assert controls._on_refine_bboxes is None
        assert controls._on_expand_refine_bboxes is None
        assert controls._on_reload_ocr is None
        assert controls.page_name_box is None
        assert controls.page_source_label is None
        assert controls.page_source_tooltip is None
