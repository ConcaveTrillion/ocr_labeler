from __future__ import annotations

import logging

from nicegui import binding, ui

from ...viewmodels.project.project_state_view_model import ProjectStateViewModel
from ..callbacks import ProjectGotoCallback, ProjectNavigateCallback
from ..shared.button_styles import style_action_button

logger = logging.getLogger(__name__)


class ProjectNavigationControls:  # pragma: no cover - UI wrapper file
    """Project-level page navigation and page metadata controls."""

    def __init__(
        self,
        viewmodel: ProjectStateViewModel,
        on_prev: ProjectNavigateCallback,
        on_next: ProjectNavigateCallback,
        on_goto: ProjectGotoCallback,
    ):
        logger.debug("Initializing ProjectNavigationControls")
        self.viewmodel = viewmodel
        self._on_prev = on_prev
        self._on_next = on_next
        self._on_goto = on_goto
        self.row = None
        self.page_index_box = None
        self.dir_input = None
        self.page_input = None
        self.page_total = None
        self._notified_error_keys: set[str] = set()

    def _notify(self, message: str, type_: str = "warning") -> None:
        """Route notifications through session queue with UI fallback."""
        app_state_model = getattr(self.viewmodel, "_app_state_model", None)
        app_state = getattr(app_state_model, "_app_state", None)
        if app_state is not None:
            app_state.queue_notification(message, type_)
            return
        ui.notify(message, type=type_)

    def _notify_once(self, key: str, message: str, type_: str = "warning") -> None:
        """Emit a notification once per key to avoid repeated toasts."""
        if key in self._notified_error_keys:
            return
        self._notified_error_keys.add(key)
        self._notify(message, type_)

    def _bind_from_safe(
        self,
        target: object,
        target_property: str,
        source: object,
        source_property: str,
        *,
        key: str,
        message: str,
    ) -> None:
        """Bind with user-visible warning if binding setup fails."""
        try:
            binding.bind_from(
                target,
                target_property,
                source,
                source_property,
            )
        except Exception:
            logger.exception(
                "Binding failed: %s.%s <- %s.%s",
                type(target).__name__,
                target_property,
                type(source).__name__,
                source_property,
            )
            self._notify_once(key, message, type_="warning")

    def build(self) -> ui.element:
        logger.debug("Building ProjectNavigationControls UI")
        with ui.column().classes("gap-2") as container:
            with ui.row().classes("items-center gap-2"):
                self.prev_button = ui.button("Prev", on_click=self._on_prev)
                style_action_button(self.prev_button, size="md")
                self.next_button = ui.button("Next", on_click=self._on_next)
                style_action_button(self.next_button, size="md")
                self.goto_button = ui.button(
                    "Go To:",
                    on_click=lambda event: self._on_goto(self.page_input.value, event),
                )
                style_action_button(self.goto_button, size="md")
                self.page_input = (
                    ui.number(label="Page", value=1, min=1, format="%d")
                    .on(
                        "keydown.enter",
                        lambda event: self._on_goto(self.page_input.value, event),
                    )
                    .props("autocomplete=off")
                )
                self.page_total = ui.label("")
                self._bind_from_safe(
                    self.prev_button,
                    "disable",
                    self.viewmodel,
                    "prev_disabled",
                    key="nav-prev-disabled-binding",
                    message="Previous button may not reflect disabled state",
                )
                self._bind_from_safe(
                    self.next_button,
                    "disable",
                    self.viewmodel,
                    "next_disabled",
                    key="nav-next-disabled-binding",
                    message="Next button may not reflect disabled state",
                )
                self._bind_from_safe(
                    self.goto_button,
                    "disable",
                    self.viewmodel,
                    "goto_disabled",
                    key="nav-goto-disabled-binding",
                    message="Go To button may not reflect disabled state",
                )
                if self.page_input:
                    self._bind_from_safe(
                        self.page_input,
                        "disable",
                        self.viewmodel,
                        "is_controls_disabled",
                        key="nav-page-input-disabled-binding",
                        message="Page input may not reflect disabled state",
                    )

        return container

    def set_page(self, index_plus_one: int, total: int):
        logger.debug(
            "Setting project navigation page to %s, total: %s",
            index_plus_one,
            total,
        )
        if self.page_input:
            self.page_input.value = index_plus_one
        if self.page_total:
            self.page_total.text = f"/ {total}" if total else "/ 0"
