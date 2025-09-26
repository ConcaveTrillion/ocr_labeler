from __future__ import annotations

import asyncio
import logging

from nicegui import binding, ui

from ...state import ProjectState
from ...viewmodels.project.project_state_view_model import ProjectStateViewModel

logger = logging.getLogger(__name__)


class ProjectControls:  # pragma: no cover - UI wrapper file
    """Navigation + open directory row."""

    container: ui.element | None = None
    row: ui.element | None = None
    prev_button: ui.button | None = None
    next_button: ui.button | None = None
    goto_button: ui.button | None = None
    page_input: ui.number | None = None
    page_total: ui.label | None = None
    navigation_working_spinner: ui.spinner | None = None

    project_state: ProjectState | None = None

    def __init__(
        self,
        project_state: ProjectState,
    ):
        logger.debug("Initializing ProjectControls")

        self.project_state = project_state
        # UI refs
        self.row = None
        self.page_index_box = (
            None  # non-interactive button-style box showing current page name
        )
        self.page_total = None

        self.project_controls_model: ProjectStateViewModel = ProjectStateViewModel(
            self.project_state
        )

        logger.debug("ProjectControls initialization complete")

    def build(self) -> ui.element:
        logger.debug("Building ProjectControls UI")
        with ui.column().classes("gap-2") as self.container:
            with ui.row().classes("items-center gap-2") as self.row:
                self.prev_button = ui.button("Prev", on_click=self.state.prev_page())
                self.next_button = ui.button("Next", on_click=self.state.next_page())
                self.goto_button = ui.button(
                    "Go To:", on_click=lambda: self.on_goto(self.page_input.value)
                )
                self.page_input = (
                    ui.number(label="Page", value=1, min=1, format="%d").on(
                        "keydown.enter",
                        lambda e: self.on_goto(self.page_input.value),
                    )
                    # .on("blur", lambda e: self.on_goto(self.page_input.value))
                )
                self.page_total = ui.label("")
                self.navigation_working_spinner = (
                    ui.spinner(type="gears").props("small").hide()
                )

        binding.bind_from(
            self.navigation_working_spinner,
            "hidden",
            self.project_controls_model,
            "is_navigating",
            invert=True,
        )
        binding.bind_from(
            self.page_total,
            "text",
            self.project_controls_model,
            "page_total",
        )

        return self.container

    def update(self):
        logger.debug("Updating ProjectControls UI with current state")
        if not self.state or not self.state.project_pages:
            logger.warning("No project state or pages available for update")
            return

        current_index = self.state.current_page_index
        total_pages = len(self.state.project_pages)

        # Update page input and total label
        if self.page_input:
            self.page_input.value = current_index + 1  # 1-based for user
            self.page_input.props("max", total_pages)
        if self.page_total:
            self.page_total.set_text(f"of {total_pages}")

        # Enable/disable buttons based on current index
        if self.prev_button:
            self.prev_button.props(
                "disabled", (not self.project_controls_model.can_navigate_prev)
            )
        if self.next_button:
            self.next_button.props(
                "disabled", (not self.project_controls_model.can_navigate_next)
            )
        if self.goto_button:
            self.goto_button.props(
                "disabled",
                (not self.project_controls_model.can_navigate) or total_pages == 0,
            )

        logger.debug(
            f"Set page input to {self.page_input.value}, total pages {total_pages}"
        )
        logger.debug(
            f"Prev button {'disabled' if current_index <= 0 else 'enabled'}, "
            f"Next button {'disabled' if current_index >= total_pages - 1 else 'enabled'}"
        )

    async def _prev_page(self):
        logger.debug("Prev button clicked")
        with self.navigation_context():
            await asyncio.to_thread(
                self.project_state.prev_page
            )  # Assuming prev_page is async

    async def _next_page(self):
        logger.debug("Next button clicked")
        with self.navigation_context():
            await asyncio.to_thread(
                self.project_state.next_page
            )  # Assuming next_page is async

    def _disable_buttons(self):
        logger.debug("Disabling navigation buttons")
        # Disable buttons to prevent multiple clicks during operation
        for button in self.row.find_all("button"):
            button.props("disabled", True)

    def _enable_buttons(self):
        logger.debug("Enabling navigation buttons")
        # Re-enable buttons after operation
        for button in self.row.find_all("button"):
            button.props("disabled", False)
