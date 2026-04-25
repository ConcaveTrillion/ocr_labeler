from __future__ import annotations

import logging

from nicegui import ui

from ...viewmodels.project.project_state_view_model import ProjectStateViewModel
from ..callbacks import ProjectGotoCallback, ProjectNavigateCallback
from ..shared.button_styles import style_action_button
from ..shared.view_helpers import NotificationMixin

logger = logging.getLogger(__name__)


class ProjectNavigationControls(
    NotificationMixin
):  # pragma: no cover - UI wrapper file
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
        self._app_state_view_model = getattr(viewmodel, "_app_state_model", None)
        self._on_prev = on_prev
        self._on_next = on_next
        self._on_goto = on_goto
        self.row = None
        self.page_input = None
        self.page_total = None
        self._notified_error_keys: set[str] = set()

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
                self._bind_disabled_from_safe(
                    self.prev_button,
                    self.viewmodel,
                    "prev_disabled",
                    key="nav-prev-disabled-binding",
                    message="Previous button may not reflect disabled state",
                )
                self._bind_disabled_from_safe(
                    self.next_button,
                    self.viewmodel,
                    "next_disabled",
                    key="nav-next-disabled-binding",
                    message="Next button may not reflect disabled state",
                )
                self._bind_disabled_from_safe(
                    self.goto_button,
                    self.viewmodel,
                    "goto_disabled",
                    key="nav-goto-disabled-binding",
                    message="Go To button may not reflect disabled state",
                )
                if self.page_input:
                    self._bind_disabled_from_safe(
                        self.page_input,
                        self.viewmodel,
                        "is_controls_disabled",
                        key="nav-page-input-disabled-binding",
                        message="Page input may not reflect disabled state",
                    )

        self.sync_control_states()

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

    def sync_control_states(self) -> None:
        """Apply the latest disabled state directly to controls.

        NiceGUI bindings can miss propagating the disabled prop to the DOM when
        a page is restored from pre-saved fixture data during route loads.
        Reapplying the current flags during view refresh keeps the Quasar state
        aligned with the view model.
        """
        if getattr(self, "prev_button", None) is not None:
            self.prev_button.set_enabled(
                not bool(getattr(self.viewmodel, "prev_disabled", False))
            )
            self.prev_button.update()
        if getattr(self, "next_button", None) is not None:
            self.next_button.set_enabled(
                not bool(getattr(self.viewmodel, "next_disabled", False))
            )
            self.next_button.update()
        if getattr(self, "goto_button", None) is not None:
            self.goto_button.set_enabled(
                not bool(getattr(self.viewmodel, "goto_disabled", False))
            )
            self.goto_button.update()
        if self.page_input is not None:
            self.page_input.set_enabled(
                not bool(getattr(self.viewmodel, "is_controls_disabled", False))
            )
            self.page_input.update()
