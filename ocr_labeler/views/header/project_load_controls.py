from __future__ import annotations

import logging

from nicegui import binding, ui

from ...models.app_state_view_model import AppStateViewModel
from ...models.project_state_view_model import ProjectStateViewModel

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

            binding.bind_from(
                self.path_label,
                "text",
                self.project_state_model,
                "project_root_resolved",
            )
        return row

    async def _load_selected_project(self):
        """Load the selected project using the ViewModel."""
        key = self.app_state_model.selected_project_key
        if not key:
            ui.notify("No project selected", type="warning")
            return

        try:
            ui.notify(f"Loading {key}", type="info")
            await self.app_state_model.load_selected_project()
            ui.notify(f"Loaded {key}", type="positive")
        except Exception as exc:  # noqa: BLE001
            ui.notify(f"Load failed: {exc}", type="negative")
            logger.error(f"Failed to load project '{key}': {exc}")
