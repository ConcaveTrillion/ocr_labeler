from __future__ import annotations

import logging

from nicegui import binding, events, ui

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
        self._notified_error_keys: set[str] = set()

    def _notify(self, message: str, type_: str = "info"):
        """Route notifications through per-session queue with UI fallback."""
        app_state = getattr(self.app_state_model, "_app_state", None)
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

    def _bind_safe(
        self,
        target: object,
        target_property: str,
        source: object,
        source_property: str,
        *,
        key: str,
        message: str,
    ) -> None:
        """Two-way bind with user-visible warning if setup fails."""
        try:
            binding.bind(
                target,
                target_property,
                source,
                source_property,
            )
        except Exception:
            logger.exception(
                "Two-way binding failed: %s.%s <-> %s.%s",
                type(target).__name__,
                target_property,
                type(source).__name__,
                source_property,
            )
            self._notify_once(key, message, type_="warning")

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

            self._bind_from_safe(
                self.select,
                "options",
                self.app_state_model,
                "project_keys",
                key="project-load-select-options-binding",
                message="Project list may not update automatically",
            )
            self._bind_safe(
                self.select,
                "value",
                self.app_state_model,
                "selected_project_key",
                key="project-load-select-value-binding",
                message="Project selection sync may not update automatically",
            )

            # Bind controls disabled state to combined busy/loading state
            controls = [self.select, self.load_project_button]
            for control in controls:
                self._bind_from_safe(
                    control,
                    "disable",
                    self.project_state_model,
                    "is_controls_disabled",
                    key="project-load-controls-disabled-binding",
                    message="Load controls may not reflect disabled state",
                )

            self._bind_from_safe(
                self.path_label,
                "text",
                self.project_state_model,
                "project_root_resolved",
                key="project-load-path-binding",
                message="Project path label may not update automatically",
            )
        return row

    async def _load_selected_project(
        self,
        _event: events.ClickEventArguments | None = None,
    ):
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
            await self.app_state_model.command_load_selected_project()
            # Update browser URL to reflect the loaded project
            url = build_project_url(key)
            ui.navigate.history.replace(url)
            logger.debug(f"Browser URL updated to: {url}")
        except Exception as exc:  # noqa: BLE001
            self._notify(f"Load failed: {exc}", "negative")
            logger.error(f"Failed to load project '{key}': {exc}")
