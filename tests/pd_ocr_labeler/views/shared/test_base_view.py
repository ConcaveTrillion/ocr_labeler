"""Tests for BaseView teardown lifecycle."""

from __future__ import annotations

from typing import Any

from pd_ocr_labeler.viewmodels.shared.base_viewmodel import BaseViewModel
from pd_ocr_labeler.views.shared.base_view import BaseView


class _StubViewModel(BaseViewModel):
    """Minimal concrete viewmodel for testing."""

    pass


class _StubView(BaseView[_StubViewModel]):
    """Minimal concrete view for testing."""

    def build(self) -> Any:
        return None

    def refresh(self):
        pass


def test_init_registers_listener():
    vm = _StubViewModel()
    _view = _StubView(vm)
    assert vm._property_changed_callbacks, "listener should be registered after init"


def test_teardown_removes_listener():
    vm = _StubViewModel()
    view = _StubView(vm)
    view.teardown()
    assert not vm._property_changed_callbacks, (
        "listener should be removed after teardown"
    )


def test_teardown_is_idempotent():
    vm = _StubViewModel()
    view = _StubView(vm)
    view.teardown()
    view.teardown()  # should not raise
    assert not vm._property_changed_callbacks


def test_teardown_sets_flag():
    vm = _StubViewModel()
    view = _StubView(vm)
    assert not view._is_torn_down
    view.teardown()
    assert view._is_torn_down


def test_property_change_not_received_after_teardown():
    vm = _StubViewModel()
    received: list[str] = []

    class _TrackingView(_StubView):
        def _on_viewmodel_property_changed(self, property_name: str, value: Any):
            received.append(property_name)

    view = _TrackingView(vm)
    vm.notify_property_changed("foo", 1)
    assert received == ["foo"]

    view.teardown()
    vm.notify_property_changed("bar", 2)
    assert received == ["foo"], "no notification after teardown"
