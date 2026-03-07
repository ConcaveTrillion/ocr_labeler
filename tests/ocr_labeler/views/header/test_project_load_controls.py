"""Tests for project load controls safe binding behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import ocr_labeler.views.header.project_load_controls as plc_module
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

        monkeypatch.setattr(plc_module.binding, "bind_from", failing_bind_from)
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

        monkeypatch.setattr(plc_module.binding, "bind", failing_bind)
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
