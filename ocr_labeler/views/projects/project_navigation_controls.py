from __future__ import annotations

import logging

from nicegui import ui

from ...viewmodels.project.project_state_view_model import ProjectStateViewModel

logger = logging.getLogger(__name__)


class ProjectNavigationControls:  # pragma: no cover - UI wrapper file
    """Project-level page navigation and page metadata controls."""

    def __init__(
        self,
        viewmodel: ProjectStateViewModel,
        on_prev,
        on_next,
        on_goto,
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

    def build(self) -> ui.element:
        logger.debug("Building ProjectNavigationControls UI")
        with ui.column().classes("gap-2") as container:
            with ui.row().classes("items-center gap-2"):
                self.prev_button = ui.button("Prev", on_click=self._on_prev)
                self.next_button = ui.button("Next", on_click=self._on_next)
                self.goto_button = ui.button(
                    "Go To:", on_click=lambda: self._on_goto(self.page_input.value)
                )
                self.page_input = (
                    ui.number(label="Page", value=1, min=1, format="%d")
                    .on(
                        "keydown.enter",
                        lambda e: self._on_goto(self.page_input.value),
                    )
                    .props("autocomplete=off")
                )
                self.page_total = ui.label("")

                try:
                    from nicegui import binding

                    binding.bind_from(
                        self.prev_button, "disabled", self.viewmodel, "prev_disabled"
                    )
                    binding.bind_from(
                        self.next_button, "disabled", self.viewmodel, "next_disabled"
                    )
                    binding.bind_from(
                        self.goto_button, "disabled", self.viewmodel, "goto_disabled"
                    )
                    if self.page_input:
                        binding.bind_from(
                            self.page_input,
                            "disabled",
                            self.viewmodel,
                            "is_controls_disabled",
                        )
                except Exception:
                    pass

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
