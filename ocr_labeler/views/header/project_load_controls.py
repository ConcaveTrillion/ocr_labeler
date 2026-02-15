from __future__ import annotations

import logging

from nicegui import binding, ui

from ...routing import build_project_url
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

    def _notify(self, message: str, type_: str = "info"):
        """Route notifications through per-session queue with UI fallback."""
        try:
            app_state = getattr(self.app_state_model, "_app_state", None)
            if app_state is not None:
                app_state.queue_notification(message, type_)
                return
        except Exception:
            logger.debug("Failed to enqueue session notification", exc_info=True)

        ui.notify(message, type=type_)

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

            # Bind controls disabled state to combined busy/loading state
            controls = [self.select, self.load_project_button]
            for control in controls:
                binding.bind_from(
                    control,
                    "disable",
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
            self._notify("No project selected", "warning")
            return

        # Prevent multiple clicks during loading
        if self.project_state_model.is_controls_disabled:
            logger.debug("Load button clicked while disabled, ignoring")
            return

        try:
            self._notify(f"Loading {key}", "info")
            await self.app_state_model.command_load_selected_project()
            self._notify(f"Loaded {key}", "positive")
            # Update browser URL to reflect the loaded project
            try:
                url = build_project_url(key)
                ui.navigate.history.replace(url)
                logger.debug(f"Browser URL updated to: {url}")
            except Exception:
                logger.debug(
                    "Failed to update browser URL after project load", exc_info=True
                )
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Load failed: {exc}", "negative")
            logger.error(f"Failed to load project '{key}': {exc}")
