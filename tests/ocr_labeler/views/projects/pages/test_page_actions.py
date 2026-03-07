"""Tests for page-level actions component."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import ocr_labeler.views.projects.pages.page_actions as page_actions_module
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

    def test_bind_from_safe_does_not_raise_and_notifies_once(self, monkeypatch):
        """Binding setup failures are handled without raising and notify once."""
        controls = PageActions(project_viewmodel=Mock(), page_viewmodel=Mock())

        def failing_bind_from(*_args, **_kwargs):
            raise RuntimeError("bind failed")

        monkeypatch.setattr(
            page_actions_module.binding,
            "bind_from",
            failing_bind_from,
        )
        notify_mock = MagicMock()
        monkeypatch.setattr(controls, "_notify", notify_mock)

        controls._bind_from_safe(
            object(),
            "text",
            object(),
            "value",
            key="bind-key",
            message="binding failed",
        )
        controls._bind_from_safe(
            object(),
            "text",
            object(),
            "value",
            key="bind-key",
            message="binding failed",
        )

        notify_mock.assert_called_once_with("binding failed", "warning")

    def test_bind_from_safe_success_emits_no_notification(self, monkeypatch):
        """Successful binding setup should not emit warning notifications."""
        controls = PageActions(project_viewmodel=Mock(), page_viewmodel=Mock())
        notify_mock = MagicMock()
        monkeypatch.setattr(controls, "_notify", notify_mock)
        monkeypatch.setattr(
            page_actions_module.binding, "bind_from", lambda *_args, **_kwargs: None
        )

        controls._bind_from_safe(
            object(),
            "text",
            object(),
            "value",
            key="bind-key-success",
            message="should not notify",
        )

        notify_mock.assert_not_called()

    def test_bind_from_safe_failure_queues_expected_notification(self, monkeypatch):
        """Binding failure should emit expected notification content via queue path."""
        app_state = Mock()
        app_state.queue_notification = MagicMock()
        app_state_model = Mock()
        app_state_model._app_state = app_state

        project_viewmodel = Mock()
        project_viewmodel._app_state_model = app_state_model

        controls = PageActions(
            project_viewmodel=project_viewmodel,
            page_viewmodel=Mock(),
        )

        def failing_bind_from(*_args, **_kwargs):
            raise RuntimeError("bind failed")

        monkeypatch.setattr(page_actions_module.binding, "bind_from", failing_bind_from)

        controls._bind_from_safe(
            object(),
            "text",
            object(),
            "value",
            key="queue-bind-key",
            message="Page source label may not update automatically",
        )

        app_state.queue_notification.assert_called_once_with(
            "Page source label may not update automatically",
            "warning",
        )
