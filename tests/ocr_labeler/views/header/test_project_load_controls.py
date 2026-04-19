"""Tests for project load controls safe binding behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import ocr_labeler.views.shared.view_helpers as view_helpers_module
from ocr_labeler.views.header.project_load_controls import ProjectLoadControls


class TestProjectLoadControls:
    """Validate binding wrapper behavior for ProjectLoadControls."""

    def test_bind_from_safe_does_not_raise_and_notifies_once(self, monkeypatch):
        controls = ProjectLoadControls(
            app_state_model=Mock(),
            project_state_model=Mock(),
        )

        def failing_bind_from(*_args, **_kwargs):
            raise RuntimeError("bind_from failed")

        monkeypatch.setattr(view_helpers_module.binding, "bind_from", failing_bind_from)
        notify_mock = MagicMock()
        monkeypatch.setattr(controls, "_notify", notify_mock)

        controls._bind_from_safe(
            object(),
            "text",
            object(),
            "value",
            key="load-bind-key",
            message="load bind failed",
        )
        controls._bind_from_safe(
            object(),
            "text",
            object(),
            "value",
            key="load-bind-key",
            message="load bind failed",
        )

        notify_mock.assert_called_once_with("load bind failed", "warning")

    def test_bind_safe_does_not_raise_and_notifies_once(self, monkeypatch):
        controls = ProjectLoadControls(
            app_state_model=Mock(),
            project_state_model=Mock(),
        )

        def failing_bind(*_args, **_kwargs):
            raise RuntimeError("bind failed")

        monkeypatch.setattr(view_helpers_module.binding, "bind", failing_bind)
        notify_mock = MagicMock()
        monkeypatch.setattr(controls, "_notify", notify_mock)

        controls._bind_safe(
            object(),
            "value",
            object(),
            "selected",
            key="load-two-way-bind-key",
            message="two-way bind failed",
        )
        controls._bind_safe(
            object(),
            "value",
            object(),
            "selected",
            key="load-two-way-bind-key",
            message="two-way bind failed",
        )

        notify_mock.assert_called_once_with("two-way bind failed", "warning")

    def test_sync_control_states_applies_project_disabled_flag(self):
        project_state_model = Mock()
        project_state_model.is_controls_disabled = True
        controls = ProjectLoadControls(
            app_state_model=Mock(),
            project_state_model=project_state_model,
        )

        controls.select = Mock()
        controls.load_project_button = Mock()
        controls.source_folder_button = Mock()

        controls.sync_control_states()

        controls.select.set_enabled.assert_called_once_with(False)
        controls.load_project_button.set_enabled.assert_called_once_with(False)
        controls.source_folder_button.set_enabled.assert_called_once_with(False)
        controls.select.update.assert_called_once_with()
        controls.load_project_button.update.assert_called_once_with()
        controls.source_folder_button.update.assert_called_once_with()
