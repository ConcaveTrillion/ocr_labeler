"""Shared view utilities for notifications and safe NiceGUI bindings."""

from __future__ import annotations

import logging
from typing import Any

from nicegui import binding, ui

logger = logging.getLogger(__name__)


class NotificationMixin:
    """Mixin providing notification and safe-binding helpers for views.

    Subclasses must set ``_app_state_view_model`` to an
    :class:`AppStateViewModel` (or ``None``) so that notifications
    are routed through the centralised queue. When unavailable the
    mixin falls back to ``ui.notify`` for direct display.
    """

    _app_state_view_model: Any = None
    _notified_error_keys: set[str]

    def _ensure_notified_keys(self) -> set[str]:
        if not hasattr(self, "_notified_error_keys"):
            self._notified_error_keys = set()
        return self._notified_error_keys

    # ----- notifications -----

    def _notify(self, message: str, type_: str = "info") -> None:
        """Queue a user notification through AppStateViewModel or fall back to ui.notify."""
        vm = self._app_state_view_model
        if vm is not None:
            vm.queue_notification(message, type_)
            return
        ui.notify(message, type=type_)

    def _notify_once(self, key: str, message: str, type_: str = "warning") -> None:
        """Emit a notification at most once per *key* within this view's lifetime."""
        keys = self._ensure_notified_keys()
        if key in keys:
            return
        keys.add(key)
        self._notify(message, type_)

    # ----- safe bindings -----

    def _bind_from_safe(
        self,
        target: Any,
        target_property: str,
        source: Any,
        source_property: str,
        *,
        key: str,
        message: str,
    ) -> None:
        """Bind a target property from a source, logging failures."""
        try:
            binding.bind_from(target, target_property, source, source_property)
        except Exception:
            logger.exception(
                "Binding failed: %s.%s <- %s.%s",
                type(target).__name__,
                target_property,
                type(source).__name__,
                source_property,
            )
            self._notify_once(key, message, type_="warning")

    def _bind_safe(
        self,
        target: Any,
        target_property: str,
        source: Any,
        source_property: str,
        *,
        key: str,
        message: str,
    ) -> None:
        """Two-way bind a target property to a source, logging failures."""
        try:
            binding.bind(target, target_property, source, source_property)
        except Exception:
            logger.exception(
                "Two-way binding failed: %s.%s <-> %s.%s",
                type(target).__name__,
                target_property,
                type(source).__name__,
                source_property,
            )
            self._notify_once(key, message, type_="warning")

    def _bind_disabled_from_safe(
        self,
        target: Any,
        source: Any,
        source_property: str,
        *,
        key: str,
        message: str,
    ) -> None:
        """Bind ``target.enabled`` from the negation of *source_property*."""
        try:
            target.bind_enabled_from(
                source, source_property, backward=lambda disabled: not bool(disabled)
            )
        except Exception:
            logger.exception(
                "Disabled binding failed: %s.enabled <- not %s.%s",
                type(target).__name__,
                type(source).__name__,
                source_property,
            )
            self._notify_once(key, message, type_="warning")
