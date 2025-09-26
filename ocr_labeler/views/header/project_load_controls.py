from __future__ import annotations

import logging

from nicegui import binding, ui

from ...viewmodels.app.app_state_view_model import AppStateViewModel
from ...viewmodels.project.project_state_view_model import ProjectStateViewModel

logger = logging.getLogger(__name__)


class ProjectLoadControls:
    """Project selection + path label row.

    Responsibilities:
    - Let user choose and load a project
    - Show the fully resolved selected project directory path (right aligned, wrapped)
    """

    def __init__(
        self,
        app_state_model: AppStateViewModel,
        project_state_model: ProjectStateViewModel,
    ):
        self.app_state_model = app_state_model
        self.project_state_model = project_state_model

    def build(self) -> ui.element:
        with ui.row().classes("w-full items-center gap-2") as row:
            self._row = row

            # Bind select options and value to AppState model
            self.select = ui.select(
                label="Project",
                options=self.app_state_model.project_keys,
                value=self.app_state_model.selected_project_key,
                with_input=False,
            )

            # LOAD button bound disabled state to is_loading
            self.load_project_button = ui.button(
                "LOAD", on_click=self._load_selected_project
            )

            # Loading spinner - shows during project loading
            self.loading_spinner = (
                ui.spinner(type="gears").props("small").classes("hidden")
            )

            ui.space()

            self.path_label = (
                ui.label("")
                .classes(
                    "text-xs text-gray-500 font-mono text-right flex-1 overflow-hidden"
                )
                .style("white-space:normal; word-break:break-all;")
            )

            binding.bind_from(
                self.select, "options", self.app_state_model, "project_keys"
            )
            binding.bind(
                self.select, "value", self.app_state_model, "selected_project_key"
            )
            binding.bind_from(
                self.select, "tooltip", self.app_state_model, "selected_project_path"
            )

            # bind controls disabled state to combined busy/loading state
            controls = [self.select, self.load_project_button]
            for control in controls:
                binding.bind_from(
                    control,
                    "disabled",
                    self.project_state_model,
                    "is_controls_disabled",
                )

            # Set up manual spinner visibility handling
            self._update_spinner_visibility()
            self.app_state_model._app_state.on_change.append(self._on_app_state_change)

            binding.bind_from(
                self.path_label,
                "text",
                self.project_state_model,
                "project_root_resolved",
            )
        return row

    def _update_spinner_visibility(self):
        """Update spinner visibility based on current loading state."""
        if self.app_state_model.is_project_loading:
            self.loading_spinner.classes(remove="hidden")
        else:
            self.loading_spinner.classes(add="hidden")

    def _on_app_state_change(self):
        """Handle app state changes to update spinner visibility."""
        self._update_spinner_visibility()

    async def _load_selected_project(self):
        """Load the selected project using the ViewModel."""
        key = self.app_state_model.selected_project_key
        if not key:
            ui.notify("No project selected", type="warning")
            return

        try:
            ui.notify(f"Loading {key}", type="info")
            await self.app_state_model.command_load_selected_project()
            ui.notify(f"Loaded {key}", type="positive")
        except Exception as exc:  # noqa: BLE001
            ui.notify(f"Load failed: {exc}", type="negative")
            logger.error(f"Failed to load project '{key}': {exc}")
