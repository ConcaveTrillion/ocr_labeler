"""Tests for page-layer view composition."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from ocr_labeler.views.projects.pages.page_view import PageView


class TestPageView:
    """Test PageView factory behavior."""

    def test_from_project_returns_none_without_project_state(self):
        """Factory returns None when project state is unavailable."""
        project_view_model = SimpleNamespace(_project_state=None)

        page_view = PageView.from_project(project_view_model)

        assert page_view is None

    def test_from_project_builds_page_view_with_callbacks(self):
        """Factory wires page callbacks to PageView action handlers."""
        project_state = Mock()
        project_view_model = SimpleNamespace(_project_state=project_state)

        page_view = PageView.from_project(project_view_model)

        assert page_view is not None
        assert page_view.project_view_model is project_view_model
        assert page_view.page_state_view_model is not None
        assert page_view.page_action_callbacks.save_page == page_view._save_page_async
        assert page_view.page_action_callbacks.load_page == page_view._load_page_async
        assert (
            page_view.page_action_callbacks.refine_bboxes
            == page_view._refine_bboxes_async
        )
        assert (
            page_view.page_action_callbacks.expand_refine_bboxes
            == page_view._expand_refine_bboxes_async
        )
        assert page_view.page_action_callbacks.reload_ocr == page_view._reload_ocr_async
